import { useEffect, useRef, useState } from 'react';
import { FormDialog } from '../forms/FormDialog';
import { DashboardCanvas } from '../shared/DashboardCanvas';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import { Emoji } from '../shared/Emoji';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, pageRequest, setPageLocation } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { usePageActions } from '../shared/usePageActions';
import { addWidget, layoutsEqual } from '../spaces/summaryLayout';
import { DashboardActions, confirmDelete } from './Actions';
import Catalog from './Catalog';
import GadgetCard from './Gadget';
import type { DetailData, Gadget } from './types';
import { startAutoRefresh } from './autoRefresh';

export default function DetailPage(props: PageProps) {
  return <DashboardView {...props} />;
}

export function DashboardView(props: PageProps) {
  const { initial, csrfToken } = props;
  const [data, setData] = useState(initial.data as DetailData);
  const [draft, setDraft] = useState(data.grid.widgets);
  const [editing, setEditing] = useState(data.editing);
  const [catalog, setCatalog] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const actions = usePageActions(props, data.modal);
  const life = useRef(new AbortController());
  const pending = useRef(false);
  const nextDraftId = useRef(0);
  const editButton = useRef<HTMLButtonElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const dashboard = data.dashboard;
  const dirty = !layoutsEqual(data.grid.widgets, draft);
  const locked = busy || actions.busy || !!actions.modal;
  useDirtyGuard(editing && dirty, busy || actions.busy);
  const automaticRefresh = useRef<() => Promise<void>>();
  automaticRefresh.current = async () => {
    if (
      pending.current ||
      editing ||
      locked ||
      catalog ||
      document.querySelector('.tasks-modal.is-open') ||
      !navigator.onLine
    )
      return;
    await refresh(true);
  };
  useEffect(() => {
    if (editing) return;
    return startAutoRefresh(dashboard.refresh_interval, () => automaticRefresh.current!());
  }, [editing, dashboard.refresh_interval]);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    document.title = `${dashboard.name} | ancore`;
  }, [dashboard.name]);

  function accept(next: DetailData) {
    setData(next);
    setDraft(next.grid.widgets);
  }
  function finishEditing() {
    setEditing(false);
    setCatalog(false);
    setPageLocation(dashboard.url);
    requestAnimationFrame(() => editButton.current?.focus());
  }
  function cancel() {
    setDraft(data.grid.widgets);
    setError('');
    setNotice('Anulowano zmiany układu.');
    finishEditing();
  }
  async function read(target: string) {
    const page = await pageRequest<Page>(initial.api_url, target, csrfToken, life.current.signal);
    if (page.type !== 'pulpit-detail') throw new Error('Nie udało się odświeżyć pulpitu.');
    return page.data as DetailData;
  }
  async function refresh(automatic = false) {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const next = await read(editing ? data.editor_url : dashboard.url);
      if (!life.current.signal.aborted) {
        accept(next);
        if (!automatic) setNotice('Pulpit odświeżony.');
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  async function save() {
    if (pending.current || locked) return;
    if (!dirty) {
      finishEditing();
      return;
    }
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<{ page: Page }>(
        initial.api_url,
        data.grid.save_url,
        csrfToken,
        life.current.signal,
        {
          revision: data.grid.revision,
          widgets: draft.map((widget) =>
            widget.id.startsWith('new-') ? { ...widget, kind: 'progress' } : widget,
          ),
        },
      );
      if (!life.current.signal.aborted) {
        accept(result.page.data as DetailData);
        setNotice('Układ pulpitu zapisany.');
        finishEditing();
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  function add() {
    if (locked || !editing || draft.length >= data.max_gadgets) return;
    const next = addWidget(draft, { id: `new-${++nextDraftId.current}`, w: 6, h: 8 });
    if (next === draft) {
      setNotice('Brak miejsca na kolejny gadżet.');
      return;
    }
    setDraft(next);
    setNotice('Dodano gadżet. Zapisz układ, aby zachować zmiany.');
  }
  async function configured() {
    // Configuration is available only with a saved layout. Read its new revision
    // without navigating away from the editor or losing its focus context.
    const next = await read(data.editor_url);
    if (!life.current.signal.aborted) {
      accept(next);
      actions.close();
      setNotice('Konfiguracja gadżetu zapisana.');
    }
  }
  const gadgets = new Map(data.columns.flat().map((gadget) => [String(gadget.id), gadget]));
  const progress = data.gadget_catalog.find((entry) => entry.kind === 'progress');
  const widgetCatalog = draft.map((widget) => ({
    id: widget.id,
    label: gadgets.get(widget.id)?.label || progress?.name || 'Postęp pracy',
    icon: gadgets.get(widget.id)?.icon || progress?.icon || 'chart-no-axes-combined',
    min_w: 4,
    min_h: 5,
  }));
  const reload = () => {
    if (dirty)
      window.showConfirmModal({
        title: 'Odśwież pulpit',
        message: 'Odrzucić niezapisany układ i wczytać aktualną wersję?',
        confirmText: 'Odrzuć i odśwież',
        cancelText: 'Wróć do edycji',
        onConfirm: () => void refresh(),
      });
    else void refresh();
  };
  return (
    <div
      className={`dashboard-page dashboard-overview pulpits-page pulpit-grid-page ${editing ? 'pulpit-editor-page' : ''}`}
      data-react-screen="pulpit-detail"
    >
      <header className="tasks-topbar tasks-topbar--project-directory pulpit-topbar">
        <div className="tasks-titlebar-left">
          <Emoji value={dashboard.emoji} art={dashboard.emoji_art} className="nav-icon" />
          <h1 className="tasks-topbar-title" title={dashboard.name}>
            {dashboard.name}
          </h1>
        </div>
        <div className="tasks-titlebar-actions">
          {editing ? (
            <>
              <button
                ref={addButton}
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                disabled={locked}
                onClick={() => setCatalog(true)}
              >
                <Icon name="plus" />
                <span>Dodaj gadżet</span>
              </button>
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                disabled={locked}
                onClick={cancel}
              >
                Anuluj
              </button>
              <button
                type="button"
                className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                disabled={locked}
                onClick={() => void save()}
              >
                <Icon name="check" />
                <span>{busy ? 'Zapisywanie…' : 'Zapisz układ'}</span>
              </button>
            </>
          ) : (
            <>
              {dashboard.editable ? (
                <button
                  ref={editButton}
                  type="button"
                  className="tasks-tag-topbar-button tasks-tag-topbar-button--secondary"
                  disabled={locked}
                  onClick={() => {
                    setEditing(true);
                    setError('');
                    setPageLocation(data.editor_url);
                    setNotice('Włączono edycję pulpitu.');
                  }}
                >
                  <Icon name="pencil" />
                  <span>Edytuj pulpit</span>
                </button>
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
                  favorite={() => void actions.act(dashboard.favorite_url, { next: dashboard.url })}
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
      <div className="dashboard-main work-content">
        <div className={`work-summary-dashboard ${editing ? 'is-editing' : ''}`} aria-busy={busy}>
          {error || actions.error ? (
            <div className="tasks-modal__errors work-summary-error" role="alert">
              <span>{error || actions.error}</span>
              <button
                type="button"
                className="tasks-filter-button"
                disabled={locked}
                onClick={reload}
              >
                Wczytaj aktualny układ
              </button>
            </div>
          ) : null}
          <span className="u-sr-only" role="status" aria-live="polite">
            {notice}
          </span>
          {draft.length ? (
            <DashboardCanvas
              widgets={draft}
              catalog={widgetCatalog}
              editing={editing}
              busy={locked}
              onChange={setDraft}
              onNotice={setNotice}
              emptyFocusRef={addButton}
              ariaLabel="Gadżety pulpitu"
              onRemove={(id: string) => {
                setDraft((current) => current.filter((widget) => widget.id !== id));
                setNotice('Usunięto gadżet. Zapisz układ, aby zachować zmiany.');
              }}
              renderActions={(id: string, close: () => void) => {
                const gadget = gadgets.get(id);
                return (
                  <button
                    type="button"
                    className="tasks-project-menu-button"
                    disabled={locked || dirty || !gadget?.edit_url}
                    title={dirty || !gadget ? 'Zapisz układ, aby skonfigurować gadżet.' : undefined}
                    onClick={() => {
                      if (gadget) {
                        close();
                        void actions.open(gadget.edit_url);
                      }
                    }}
                  >
                    <Icon name="settings-2" />
                    <span>Konfiguruj</span>
                    {dirty || !gadget ? (
                      <span className="u-sr-only"> — zapisz najpierw układ</span>
                    ) : null}
                  </button>
                );
              }}
              renderWidget={(id: string) => {
                const gadget = gadgets.get(id);
                return (
                  <GadgetCard
                    data={
                      gadget ||
                      ({
                        id: 0,
                        kind: 'progress',
                        label: progress?.name || 'Postęp pracy',
                        icon: progress?.icon || 'chart-no-axes-combined',
                        unavailable: false,
                        edit_url: '',
                        delete_url: '',
                      } as Gadget)
                    }
                    preview={!gadget}
                  />
                );
              }}
            />
          ) : (
            <EmptyState
              title="Ten pulpit jest pusty."
              description={
                dashboard.editable
                  ? editing
                    ? 'Wybierz „Dodaj gadżet”, aby uzupełnić pulpit.'
                    : 'Otwórz edycję pulpitu i wybierz gadżety, które chcesz tutaj wyświetlać.'
                  : 'Twórca pulpitu nie dodał jeszcze gadżetów.'
              }
              src={data.illustration}
            />
          )}
        </div>
      </div>
      {catalog ? (
        <Catalog
          data={data}
          count={draft.length}
          busy={locked}
          add={add}
          close={() => setCatalog(false)}
        />
      ) : null}
      {actions.modal ? (
        <FormDialog
          data={actions.modal}
          api={initial.api_url}
          csrfToken={csrfToken}
          onClose={actions.close}
          onSaved={configured}
        />
      ) : null}
    </div>
  );
}
