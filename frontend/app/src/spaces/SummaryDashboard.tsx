import { ViewToolbar } from './ViewToolbar';
import { type ReactNode, useEffect, useRef, useState } from 'react';
import { DashboardCanvas } from '../shared/DashboardCanvas';
import { EmptyState } from '../shared/EmptyState';
import { Icon } from '../shared/Icon';
import WidgetCatalog from '../shared/WidgetCatalog';
import { errorMessage } from '../shared/api';
import { pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { addWidget, layoutsEqual, type SummaryWidget } from './summaryLayout';

const widgetDescriptions: Record<string, string> = {
  completed: 'Liczba zadań zakończonych w ostatnich 7 dniach.',
  updated: 'Liczba zadań zaktualizowanych w ostatnich 7 dniach.',
  created: 'Liczba zadań utworzonych w ostatnich 7 dniach.',
  due: 'Zadania z terminem przypadającym w najbliższych 7 dniach.',
  statuses: 'Podział otwartych i niedawno zakończonych zadań według statusu.',
  activity: 'Najnowsze zmiany w zadaniach tej Przestrzeni.',
  priorities: 'Liczba otwartych zadań według priorytetu.',
  types: 'Udział poszczególnych typów zgłoszeń w zadaniach Przestrzeni.',
  workload: 'Rozkład otwartych zadań według wykonawcy.',
  epics: 'Postęp zadań należących do epików.',
};
const metricIds = new Set(['completed', 'updated', 'created', 'due']);

export interface SummaryDashboardData {
  revision: number;
  widgets: SummaryWidget[];
  columns: number;
  save_url: string;
  catalog: {
    id: string;
    label: string;
    icon: string;
    min_w: number;
    min_h: number;
    default_w: number;
    default_h: number;
  }[];
}

export default function SummaryDashboard({
  initial,
  api,
  csrfToken,
  readOnly,
  renderWidget,
  refresh,
  filters,
}: {
  initial: SummaryDashboardData;
  api: string;
  csrfToken: string;
  readOnly: boolean;
  renderWidget: (id: string) => ReactNode;
  refresh: () => Promise<void>;
  filters?: ReactNode;
}) {
  const [saved, setSaved] = useState(initial);
  const [draft, setDraft] = useState(initial.widgets);
  const [editing, setEditing] = useState(false);
  const [catalog, setCatalog] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const editButton = useRef<HTMLButtonElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const life = useRef(new AbortController());
  const pending = useRef(false);
  const dirty = !layoutsEqual(saved.widgets, draft);
  useDirtyGuard(editing && dirty, busy);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    setSaved(initial);
    setDraft(initial.widgets);
  }, [initial]);
  function finishEditing() {
    setEditing(false);
    setCatalog(false);
    requestAnimationFrame(() => editButton.current?.focus());
  }
  function cancel() {
    setDraft(saved.widgets);
    setError('');
    setNotice('Anulowano zmiany układu.');
    finishEditing();
  }
  async function save() {
    if (pending.current) return;
    if (!dirty) {
      finishEditing();
      return;
    }
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      const result = await pageRequest<{ dashboard: SummaryDashboardData }>(
        api,
        saved.save_url,
        csrfToken,
        life.current.signal,
        { revision: saved.revision, widgets: draft },
      );
      if (!life.current.signal.aborted) {
        setSaved(result.dashboard);
        setDraft(result.dashboard.widgets);
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
  async function reload() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    try {
      await refresh();
      if (!life.current.signal.aborted) {
        setNotice('Pulpit odświeżony.');
        finishEditing();
      }
    } catch (exception) {
      if (!life.current.signal.aborted) setError(errorMessage(exception));
    } finally {
      pending.current = false;
      if (!life.current.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className={`work-summary-dashboard ${editing ? 'is-editing' : ''}`} aria-busy={busy}>
      <ViewToolbar
        className="work-summary-toolbar app-toolbar--embedded"
        actions={
          <>
            {editing ? (
              <>
                <button
                  ref={addButton}
                  type="button"
                  className="tasks-filter-button"
                  disabled={busy}
                  onClick={() => setCatalog(true)}
                >
                  <Icon name="plus" />
                  Dodaj gadżet
                </button>
                <button
                  type="button"
                  className="tasks-filter-button"
                  disabled={busy}
                  onClick={cancel}
                >
                  Anuluj
                </button>
                <button
                  type="button"
                  className="tasks-filter-button work-summary-save"
                  disabled={busy}
                  onClick={() => void save()}
                >
                  <Icon name="check" />
                  {busy ? 'Zapisywanie…' : 'Zapisz układ'}
                </button>
              </>
            ) : (
              <>
                {!readOnly && saved.save_url ? (
                  <button
                    ref={editButton}
                    type="button"
                    className="tasks-filter-button"
                    disabled={busy}
                    onClick={() => {
                      setEditing(true);
                      setError('');
                      setNotice('Włączono edycję pulpitu.');
                    }}
                  >
                    <Icon name="pencil" />
                    Edytuj pulpit
                  </button>
                ) : null}
              </>
            )}
          </>
        }
      >
        {filters}
        {editing ? (
          <span className="work-caption">{dirty ? 'Niezapisane zmiany' : 'Tryb edycji'}</span>
        ) : null}
      </ViewToolbar>
      {editing ? (
        <p className="work-caption work-summary-edit-hint">
          <span className="work-summary-edit-hint-desktop">
            Przeciągnij kafelek za uchwyt, a jego rozmiar zmień w prawym dolnym rogu. Możesz też
            użyć strzałek na uchwytach.
          </span>
          <span className="work-summary-edit-hint-mobile">
            Dodawaj gadżety i zapisuj zmiany układu.
          </span>
        </p>
      ) : null}
      {error ? (
        <div className="tasks-modal__errors work-summary-error" role="alert">
          <span>{error}</span>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={busy}
            onClick={() => {
              if (dirty)
                window.showConfirmModal({
                  title: 'Odśwież pulpit',
                  message: 'Odrzucić niezapisany układ i wczytać aktualną wersję?',
                  confirmText: 'Odrzuć i odśwież',
                  cancelText: 'Wróć do edycji',
                  onConfirm: () => void reload(),
                });
              else void reload();
            }}
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
          catalog={saved.catalog.map((item) => ({
            ...item,
            is_metric: metricIds.has(item.id),
          }))}
          editing={editing}
          busy={busy}
          onChange={setDraft}
          renderWidget={renderWidget}
          onNotice={setNotice}
          ariaLabel="Gadżety pulpitu przestrzeni"
        />
      ) : (
        <EmptyState
          title="Ten pulpit jest pusty."
          description={
            readOnly
              ? 'W tym widoku nie dodano jeszcze gadżetów.'
              : 'Otwórz edycję pulpitu i wybierz gadżety, które chcesz tutaj wyświetlać.'
          }
          illustration="work"
        />
      )}
      {catalog ? (
        <WidgetCatalog
          items={saved.catalog.map((item) => ({
            id: item.id,
            label: item.label,
            description: widgetDescriptions[item.id] || '',
            preview: renderWidget(item.id),
            previewWidth: metricIds.has(item.id) ? 320 : 560,
            previewHeight: metricIds.has(item.id) ? 140 : 420,
            previewCaption: 'Podgląd bieżących danych',
            added: draft.some((widget) => widget.id === item.id),
          }))}
          disabled={busy}
          onAdd={(id) => {
            const item = saved.catalog.find((entry) => entry.id === id);
            if (!item || busy || draft.some((widget) => widget.id === id)) return;
            setDraft((current) => addWidget(current, { id, w: item.default_w, h: item.default_h }));
            setNotice(`Dodano gadżet: ${item.label}.`);
          }}
          onClose={() => setCatalog(false)}
        />
      ) : null}
    </div>
  );
}
