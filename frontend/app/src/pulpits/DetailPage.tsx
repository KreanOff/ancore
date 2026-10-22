import { type DragEvent, useEffect, useRef, useState } from 'react';
import { FormDialog } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Dropdown } from '../shared/Dropdown';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { usePageActions } from '../shared/usePageActions';
import { DashboardActions, confirmDelete } from './Actions';
import Catalog, { readCatalog } from './Catalog';
import GadgetCard, { LayoutPreview } from './Gadget';
import type { DetailData, Gadget, Layout } from './types';
import { SettingsPage } from './SettingsDialog';

export default function DetailPage(props: PageProps) {
  return (props.initial.data as DetailData).editing ? (
    <SettingsPage {...props} />
  ) : (
    <DashboardView {...props} />
  );
}

export function DashboardView(
  props: PageProps & {
    embedded?: boolean;
    hostId?: string;
    onStateChange?: (pending: boolean) => void;
    onChanged?: () => void;
  },
) {
  const { initial, csrfToken } = props;
  const [data, setData] = useState(initial.data as DetailData),
    [dialogReady, setDialogReady] = useState(!props.embedded),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(''),
    [notice, setNotice] = useState(''),
    [dragged, setDragged] = useState<number | null>(null),
    [dropColumn, setDropColumn] = useState<number | null>(null);
  const catalogKey = 'ancore:pulpit-catalog:' + new URL(data.editor_url, location.origin).pathname;
  const [catalog, setCatalog] = useState(() => readCatalog(catalogKey));
  const actions = usePageActions(props, data.modal);
  const life = useRef(new AbortController()),
    pending = useRef(false),
    dragId = useRef<number | null>(null),
    opener = useRef<HTMLElement | null>(null),
    catalogButton = useRef<HTMLButtonElement>(null),
    layoutButton = useRef<HTMLDivElement>(null);
  useDirtyGuard(false, busy);
  const locked = busy || actions.busy || !!actions.modal,
    dashboard = data.dashboard;
  useEffect(() => () => life.current.abort(), []);
  // On a direct gadget URL, open the child after the settings panel owns focus.
  useEffect(() => setDialogReady(true), []);
  useEffect(
    () => props.onStateChange?.(busy || actions.busy || !!actions.modal),
    [busy, actions.busy, actions.modal, props.onStateChange],
  );
  useEffect(() => {
    if (data.dashboard.revision !== (initial.data as DetailData).dashboard.revision)
      props.onChanged?.();
  }, [data.dashboard.revision, initial.data, props.onChanged]);
  useEffect(() => {
    if (!props.embedded) document.title = `${data.dashboard.name} | ancore`;
  }, [data.dashboard.name, props.embedded]);
  useEffect(() => {
    try {
      sessionStorage.setItem(catalogKey, JSON.stringify(catalog));
    } catch {
      /* Optional UI preference. */
    }
  }, [catalog, catalogKey]);
  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && dragId.current !== null) {
        dragId.current = null;
        setDragged(null);
        setDropColumn(null);
      }
    };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, []);
  function toggleCatalog(element: HTMLElement) {
    opener.current = element;
    setCatalog((current) => ({ ...current, open: !current.open }));
    if (catalog.open)
      requestAnimationFrame(() =>
        (opener.current?.isConnected ? opener.current : catalogButton.current)?.focus({
          preventScroll: true,
        }),
      );
  }
  function closeCatalog() {
    setCatalog((current) => ({ ...current, open: false }));
    requestAnimationFrame(() =>
      (opener.current?.isConnected ? opener.current : catalogButton.current)?.focus({
        preventScroll: true,
      }),
    );
  }
  async function load(target: string) {
    const page = await pageRequest<Page>(initial.api_url, target, csrfToken, life.current.signal);
    if (page.type !== 'pulpit-detail') throw new Error('Nie udało się odświeżyć pulpitu.');
    if (!life.current.signal.aborted) setData(page.data as DetailData);
  }
  async function refresh() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      await load(data.list_url);
      if (!life.current.signal.aborted) setNotice('Pulpit odświeżony.');
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function arrange(layout: Layout, columns: Gadget[][], focus?: HTMLElement | null) {
    if (pending.current || !data.editing || actions.modal) return;
    const ids = (rows: Gadget[][]) => rows.map((column) => column.map((item) => item.id));
    if (
      layout === dashboard.layout &&
      JSON.stringify(ids(columns)) === JSON.stringify(ids(data.columns))
    )
      return;
    const before = data;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice('Zapisywanie układu…');
    setData({ ...data, columns, dashboard: { ...dashboard, layout } });
    try {
      const result = await pageRequest<{ revision: number }>(
        initial.api_url,
        data.arrange_url,
        csrfToken,
        life.current.signal,
        { layout, columns: ids(columns), revision: dashboard.revision },
      );
      if (!life.current.signal.aborted) {
        setData((current) => ({
          ...current,
          dashboard: { ...current.dashboard, revision: result.revision },
        }));
        setNotice('Układ pulpitu zapisany.');
      }
    } catch (exception) {
      if (!life.current.signal.aborted) {
        setData(before);
        setError(errorMessage(exception));
        setNotice('Układ nie został zapisany. Przywrócono poprzedni układ.');
      }
    } finally {
      pending.current = false;
      setBusy(false);
      requestAnimationFrame(() => {
        if (focus?.isConnected) focus.focus({ preventScroll: true });
      });
    }
  }
  function changeLayout(value: Layout) {
    const count = value === 'single' ? 1 : value === 'three' ? 3 : 2;
    const columns: Gadget[][] = Array.from({ length: count }, () => []);
    data.columns.forEach((column, index) => columns[Math.min(index, count - 1)].push(...column));
    void arrange(value, columns, layoutButton.current?.querySelector('button'));
  }
  function move(item: Gadget, column: number, index: number, direction: string) {
    const columns = data.columns.map((row) => [...row]);
    if (direction === 'column') {
      if (columns.length < 2) return;
      columns[column].splice(index, 1);
      columns[(column + 1) % columns.length].push(item);
    } else {
      const destination = index + (direction === 'up' ? -1 : 1);
      if (destination < 0 || destination >= columns[column].length) return;
      columns[column].splice(index, 1);
      columns[column].splice(destination, 0, item);
    }
    const focus = document.querySelector<HTMLElement>(
      `[data-gadget-id="${item.id}"] .documents-item-actions > button`,
    );
    void arrange(dashboard.layout, columns, focus);
  }
  async function add(kind: string) {
    if (pending.current || locked || !data.editing) return;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice('Dodawanie gadżetu…');
    try {
      const result = await pageRequest<{ gadget: Gadget; column: number; revision: number }>(
        initial.api_url,
        data.quick_add_url,
        csrfToken,
        life.current.signal,
        { kind, revision: dashboard.revision },
      );
      if (!life.current.signal.aborted) {
        setData((current) => ({
          ...current,
          columns: current.columns.map((column, index) =>
            index === result.column ? [...column, result.gadget] : column,
          ),
          dashboard: { ...current.dashboard, revision: result.revision },
        }));
        setNotice('Gadżet dodany i zapisany.');
      }
    } catch (exception) {
      if (!life.current.signal.aborted) {
        setError(errorMessage(exception));
        setNotice('Gadżet nie został dodany.');
      }
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  async function remove(item: Gadget) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        initial.api_url,
        item.delete_url,
        csrfToken,
        life.current.signal,
        new FormData(),
      );
      props.onChanged?.();
      await load(result.redirect);
      if (!life.current.signal.aborted) setNotice('Gadżet usunięty.');
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      setBusy(false);
    }
  }
  function endDrag() {
    dragId.current = null;
    setDragged(null);
    setDropColumn(null);
  }
  function drop(event: DragEvent, column: number) {
    if (dragId.current === null || locked) return;
    event.preventDefault();
    event.stopPropagation();
    const id = dragId.current,
      item = data.columns.flat().find((row) => row.id === id);
    const element =
      event.target instanceof Element
        ? event.target.closest<HTMLElement>('[data-gadget-id]')
        : null;
    if (!item || Number(element?.dataset.gadgetId) === id) {
      endDrag();
      return;
    }
    const columns = data.columns.map((row) => row.filter((gadget) => gadget.id !== id));
    const target = element
      ? columns[column].findIndex((row) => row.id === Number(element.dataset.gadgetId))
      : -1;
    const bounds = element?.getBoundingClientRect();
    const after = !!bounds && event.clientY >= bounds.top + bounds.height / 2;
    columns[column].splice(target < 0 ? columns[column].length : target + (after ? 1 : 0), 0, item);
    const focus = document.querySelector<HTMLElement>(
      `[data-gadget-id="${item.id}"] .pulpit-drag-handle`,
    );
    endDrag();
    void arrange(dashboard.layout, columns, focus);
  }
  const count = data.columns.reduce((total, column) => total + column.length, 0);
  const canvas = (
    <div className="dashboard-main">
      {dashboard.description ? <p className="pulpit-intro">{dashboard.description}</p> : null}
      {error || actions.error ? (
        <div className="tasks-modal__errors" role="alert">
          {error || actions.error}
          {error ? (
            <button
              type="button"
              className="tasks-filter-button"
              disabled={locked}
              onClick={() => void refresh()}
            >
              <Icon name="refresh-cw" />
              Odśwież pulpit
            </button>
          ) : null}
        </div>
      ) : null}
      {count || data.editing ? (
        <div className={`pulpit-grid pulpit-grid--${dashboard.layout}`} aria-busy={busy}>
          {data.columns.map((column, columnIndex) => (
            <section
              key={columnIndex}
              className={`pulpit-column ${!column.length && data.editing ? 'is-empty' : ''} ${dropColumn === columnIndex ? 'is-drop-target' : ''}`}
              aria-label={`Kolumna ${columnIndex + 1}`}
              onDragOver={(event) => {
                if (dragId.current !== null && !locked) {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = 'move';
                  setDropColumn(columnIndex);
                }
              }}
              onDrop={(event) => drop(event, columnIndex)}
            >
              {column.map((item, index) => (
                <GadgetCard
                  key={item.id}
                  data={item}
                  editing={data.editing}
                  busy={locked}
                  first={index === 0}
                  last={index === column.length - 1}
                  single={data.columns.length === 1}
                  dragging={dragged === item.id}
                  open={() => void actions.open(item.edit_url)}
                  move={(direction) => move(item, columnIndex, index, direction)}
                  remove={() => confirmDelete('Usuń gadżet', item.label, () => void remove(item))}
                  dragStart={(event) => {
                    if (locked) {
                      event.preventDefault();
                      return;
                    }
                    dragId.current = item.id;
                    setDragged(item.id);
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', String(item.id));
                  }}
                  dragEnd={endDrag}
                />
              ))}
              {!column.length && data.editing ? (
                <div className="pulpit-column-placeholder">
                  <img
                    className="pulpit-column-placeholder__illustration"
                    src={data.column_illustration}
                    alt=""
                    width={720}
                    height={540}
                    draggable={false}
                  />
                  <span>Przeciągnij gadżet do tej kolumny</span>
                </div>
              ) : null}
            </section>
          ))}
        </div>
      ) : (
        <section
          className="tasks-empty-state tasks-empty-state--centered tasks-empty-state--illustrated pulpit-empty-state"
          role="status"
        >
          <img
            className="tasks-empty-state__illustration pulpit-empty-state__illustration"
            src={data.illustration}
            alt=""
            width={1448}
            height={1086}
            draggable={false}
          />
          <div className="tasks-empty-state__copy">
            <h2>Ten pulpit jest pusty.</h2>
            <p>
              {dashboard.editable
                ? 'Otwórz edycję pulpitu, aby dodać pierwszy gadżet.'
                : 'Twórca pulpitu nie dodał jeszcze gadżetów.'}
            </p>
          </div>
        </section>
      )}
    </div>
  );
  return (
    <div
      className={`dashboard-page dashboard-overview pulpits-page ${data.editing ? 'pulpit-editor-page' : ''} ${data.editing && catalog.open ? 'has-catalog' : ''}`}
      data-react-screen="pulpit-detail"
    >
      <header className="tasks-topbar tasks-topbar--project-directory pulpit-topbar">
        <div className="tasks-titlebar-left">
          <h1 className="tasks-topbar-title" title={dashboard.name}>
            {dashboard.name}
          </h1>
        </div>
        <div className="tasks-titlebar-actions">
          {data.editing ? (
            <>
              <button
                ref={catalogButton}
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                aria-controls="pulpit-catalog"
                aria-expanded={catalog.open}
                onClick={(event) => toggleCatalog(event.currentTarget)}
              >
                <Icon name="plus" />
                <span>Dodaj gadżet</span>
              </button>
              <div className="pulpit-layout-control" ref={layoutButton}>
                <Dropdown
                  label="Zmień układ"
                  role="group"
                  triggerClassName="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                  menuClass="tasks-section-menu documents-item-menu pulpit-layout-menu"
                  trigger={
                    <>
                      <LayoutPreview value={dashboard.layout} />
                      <span>Zmień układ</span>
                    </>
                  }
                >
                  {(close) =>
                    data.layout_choices.map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className="tasks-project-menu-button"
                        disabled={locked}
                        aria-pressed={dashboard.layout === value}
                        onClick={() => {
                          close();
                          changeLayout(value);
                        }}
                      >
                        <LayoutPreview value={value} />
                        <span>{label}</span>
                        <Icon name="check" className="pulpit-layout-check" />
                      </button>
                    ))
                  }
                </Dropdown>
              </div>
              {!props.embedded ? (
                <a
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                  href={dashboard.url}
                  aria-label="Gotowe — wróć do pulpitu"
                >
                  <Icon name="check" />
                  <span>Gotowe</span>
                  <span className="u-sr-only"> · Wróć do pulpitu</span>
                </a>
              ) : null}
            </>
          ) : (
            <>
              {dashboard.editable ? (
                <a
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                  href={dashboard.gadgets_url}
                >
                  <Icon name="pencil" />
                  <span>Edytuj pulpit</span>
                </a>
              ) : null}
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                disabled={locked}
                onClick={() => void refresh()}
              >
                <Icon name="refresh-cw" />
                <span>Odśwież</span>
              </button>
              {dashboard.editable ? (
                <DashboardActions
                  item={dashboard}
                  busy={locked}
                  favorite={() => void actions.act(dashboard.favorite_url, { next: data.list_url })}
                  remove={() =>
                    confirmDelete(
                      'Usuń pulpit',
                      dashboard.name,
                      () => void actions.act(dashboard.delete_url, {}),
                    )
                  }
                />
              ) : null}
            </>
          )}
        </div>
      </header>
      <span className="u-sr-only" role="status" aria-live="polite">
        {notice || (data.editing ? 'Zmiany układu zapisują się automatycznie.' : '')}
      </span>
      {data.editing ? (
        <div className="pulpit-editor-body">
          {canvas}
          <Catalog
            data={data}
            state={catalog}
            change={setCatalog}
            busy={locked}
            count={count}
            add={(kind) => void add(kind)}
            close={closeCatalog}
            error={error}
          />
        </div>
      ) : (
        canvas
      )}
      {actions.modal && dialogReady ? (
        <FormDialog
          data={actions.modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          hostId={props.hostId}
          onClose={actions.close}
          onSaved={
            props.embedded
              ? async () => {
                  props.onChanged?.();
                  await load(data.editor_url);
                  actions.close();
                }
              : navigate
          }
        />
      ) : null}
    </div>
  );
}
