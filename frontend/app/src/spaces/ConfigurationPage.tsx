import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { type FormSchema } from '../forms/FormDialog';
import { Modal } from '../shared/Modal';
import SettingsPage from './SettingsPage';
import ConfigurationTable from './ConfigurationTable';
import WorkflowBoard from './WorkflowBoard';
import WorkflowStageFields from './WorkflowStageFields';
import { moveWorkflowNode, type Position } from './workflow-board';
import TypeFields from './TypeFields';
import {
  configurationEditorSchema,
  configurationFieldName,
  configurationHasRow,
  configurationAdd,
  configurationDraftKey,
  configurationDraftSubmission,
  configurationRemove,
  configurationStage,
} from './configuration-form';
import { type Page, type PageProps, pageRequest, PageError } from '../shared/page';
import { errorMessage } from '../shared/api';

export type ConfigurationSection = 'types' | 'statuses' | 'fields';
export interface ConfigurationGroup {
  key: ConfigurationSection;
  title: string;
  management: FormSchema;
  errors: string[];
  forms: FormSchema[];
}
export interface ConfigurationEditor {
  section: ConfigurationSection;
  index: number;
  remove?: boolean;
}
export interface ConfigurationData {
  name: string;
  shared: boolean;
  spaces_count: number;
  space_url: string;
  revision: string;
  errors: string[];
  section?: ConfigurationSection;
  workflow_view?: 'states' | 'map';
  editor?: ConfigurationEditor | null;
  sets: ConfigurationGroup[];
  type_icon_defaults?: Record<string, string>;
}
interface EditorState extends ConfigurationEditor {
  schema: FormSchema;
  errors: string[];
  dirty: boolean;
  adding: boolean;
}
const nouns = { types: 'typ zgłoszenia', statuses: 'etap', fields: 'pole dodatkowe' };
function createEditor(data: ConfigurationData, selection: ConfigurationEditor): EditorState | null {
  if (selection.section !== 'types' && selection.section !== 'statuses') return null;
  const group = data.sets.find((group) => group.key === selection.section);
  const schema = group?.forms[selection.index];
  if (!group || !schema) return null;
  return {
    ...selection,
    schema: configurationEditorSchema(schema),
    errors: [...data.errors, ...group.errors, ...schema.errors],
    dirty: schema.bound,
    adding: !configurationHasRow(schema),
  };
}
function focusError(form: HTMLFormElement | null) {
  const control = form?.querySelector<HTMLElement>('[aria-invalid="true"]');
  const target =
    control?.closest('.ancore-custom-select')?.querySelector<HTMLElement>('button') ||
    control ||
    form?.querySelector<HTMLElement>('[role="alert"]');
  target?.focus();
  target?.scrollIntoView({ block: 'nearest' });
}
export function ConfigurationForm({
  initial,
  csrfToken,
  onSaved,
  onStateChange,
  hostId,
  section = 'types',
  workflowView,
}: PageProps & {
  onSaved: () => Promise<void>;
  onCancel?: () => void;
  onStateChange: (dirty: boolean, pending: boolean) => void;
  hostId?: string;
  section?: 'types' | 'statuses';
  workflowView: 'states' | 'map';
}) {
  const [baseline, setBaseline] = useState(initial.data as ConfigurationData);
  const [data, setData] = useState(baseline);
  const [history, setHistory] = useState<{
    past: ConfigurationData[];
    future: ConfigurationData[];
  }>({ past: [], future: [] });
  const [untrustedBaseline, setUntrustedBaseline] = useState(() =>
    baseline.sets.some((group) => group.forms.some((schema) => schema.bound)),
  );
  const [editor, setEditor] = useState<EditorState | null>(() =>
    data.editor ? createEditor(data, data.editor) : null,
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [refreshError, setRefreshError] = useState('');
  const [conflict, setConflict] = useState(() =>
    data.errors.some((message) => message.includes('Konfiguracja zmieniła się')),
  );
  const [committed, setCommitted] = useState(false);
  const [life] = useState(() => new AbortController());
  const form = useRef<HTMLFormElement>(null);
  const sending = useRef(false);
  const source = useRef(initial.data);
  const nativeEditor = useRef(untrustedBaseline && !!data.editor);
  const newStagePosition = useRef<Position | null>(null);
  const dirty =
    !committed &&
    (untrustedBaseline || configurationDraftKey(data) !== configurationDraftKey(baseline));
  const blocked = pending || committed || !!refreshError;

  useEffect(() => {
    if (initial.data === source.current || (dirty && !committed)) return;
    source.current = initial.data;
    const clean = initial.data as ConfigurationData;
    setData(clean);
    setHistory({ past: [], future: [] });
    setBaseline(clean);
    setUntrustedBaseline(false);
    setCommitted(false);
    setConflict(false);
    setError('');
  }, [initial.data, dirty, committed]);
  useEffect(() => onStateChange(dirty, pending), [dirty, pending, onStateChange]);
  useEffect(() => () => life.abort(), [life]);

  function acceptClean(clean: ConfigurationData) {
    setData(clean);
    setHistory({ past: [], future: [] });
    setBaseline(clean);
    setUntrustedBaseline(false);
    nativeEditor.current = false;
    setEditor(null);
    setError('');
    setConflict(false);
    setCommitted(false);
  }
  function change(next: ConfigurationData) {
    if (blocked || sending.current) return;
    if (section === 'statuses' && configurationDraftKey(next) !== configurationDraftKey(data)) {
      setHistory((current) => ({ past: [...current.past.slice(-49), data], future: [] }));
    }
    setData(next);
  }
  function travel(direction: 'undo' | 'redo') {
    if (blocked || sending.current || editor || conflict) return;
    const previous = direction === 'undo' ? history.past.at(-1) : history.future[0];
    if (!previous) return;
    setHistory(
      direction === 'undo'
        ? { past: history.past.slice(0, -1), future: [data, ...history.future] }
        : { past: [...history.past, data], future: history.future.slice(1) },
    );
    setData(previous);
    setError('');
  }
  async function cancel() {
    if (pending || sending.current || committed) return;
    if (!untrustedBaseline && !conflict) {
      acceptClean(baseline);
      return;
    }
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const clean = await pageRequest<Page>(
        initial.api_url,
        data.space_url + 'configuration/',
        csrfToken,
        life.signal,
      );
      if (clean.type !== 'space-configuration') throw new Error('Nieprawidłowa odpowiedź serwera.');
      if (!life.signal.aborted) acceptClean(clean.data as ConfigurationData);
    } catch (exception) {
      if (!life.signal.aborted)
        setError('Nie udało się odrzucić zmian i odświeżyć listy. ' + errorMessage(exception));
    } finally {
      sending.current = false;
      if (!life.signal.aborted) setPending(false);
    }
  }
  async function closeEditor() {
    if (pending || sending.current) return;
    if (nativeEditor.current) {
      await cancel();
      return;
    }
    setEditor(null);
    setError('');
  }
  async function refresh() {
    if (sending.current) return;
    sending.current = true;
    setRefreshError('');
    setPending(true);
    try {
      await onSaved();
    } catch (exception) {
      if (!life.signal.aborted)
        setRefreshError(
          'Zmiany zapisano, ale nie udało się odświeżyć listy. ' + errorMessage(exception),
        );
    } finally {
      sending.current = false;
      if (!life.signal.aborted) setPending(false);
    }
  }
  function open(selection: ConfigurationEditor) {
    if (blocked || sending.current) return;
    setError('');
    setEditor(createEditor(data, selection));
  }
  function add(position?: Position) {
    if (blocked || sending.current) return;
    try {
      const next = configurationAdd(data, section);
      newStagePosition.current = section === 'statuses' && position ? position : null;
      setData(next.data);
      setError('');
      setEditor(createEditor(next.data, { section, index: next.index }));
    } catch (exception) {
      setError(errorMessage(exception));
    }
  }
  function remove(indices: number[]) {
    if (blocked || sending.current || !indices.length) return;
    try {
      change(configurationRemove(data, section, indices));
      setError('');
    } catch (exception) {
      setError(errorMessage(exception));
    }
  }
  function stage(event: FormEvent) {
    event.preventDefault();
    if (blocked || sending.current || !editor || !form.current) return;
    if (!editor.remove && !form.current.reportValidity()) return;
    try {
      let next = editor.remove
        ? configurationRemove(data, editor.section, [editor.index])
        : configurationStage(data, editor, new FormData(form.current));
      if (
        editor.section === 'statuses' &&
        editor.adding &&
        !editor.remove &&
        newStagePosition.current
      ) {
        const key = next.sets
          .find((group) => group.key === 'statuses')
          ?.forms[
            editor.index
          ]?.fields.find((field) => configurationFieldName(field) === 'key')?.value;
        if (typeof key === 'string') next = moveWorkflowNode(next, key, newStagePosition.current);
      }
      change(next);
      newStagePosition.current = null;
      nativeEditor.current = false;
      setEditor(null);
      setError('');
    } catch (exception) {
      setError(errorMessage(exception));
    }
  }
  async function save() {
    if (sending.current || blocked || !dirty || conflict || editor) return;
    sending.current = true;
    setPending(true);
    setError('');
    try {
      await pageRequest(
        initial.api_url,
        data.space_url + 'configuration/',
        csrfToken,
        life.signal,
        configurationDraftSubmission({ ...data, section }),
      );
    } catch (exception) {
      if (life.signal.aborted) return;
      let explained = false;
      if (exception instanceof PageError) {
        const response = exception.data as unknown as Page;
        if (response.type === 'space-configuration') {
          const corrected = response.data as ConfigurationData;
          const group = corrected.sets.find((group) => group.key === section);
          const index =
            group?.forms.findIndex(
              (schema) =>
                !schema.fields.some(
                  (field) => configurationFieldName(field) === 'DELETE' && field.checked,
                ) &&
                (schema.errors.length > 0 ||
                  schema.fields.some((field) => field.errors.length > 0)),
            ) ?? -1;
          const stale =
            exception.status === 409 ||
            corrected.errors.some((message) => message.includes('Konfiguracja zmieniła się'));
          explained = corrected.errors.length > 0 || !!group?.errors.length || index >= 0;
          flushSync(() => {
            setData(corrected);
            setConflict(stale);
            setPending(false);
            if (index >= 0 && !stale) setEditor(createEditor(corrected, { section, index }));
          });
          if (index >= 0 && !stale) requestAnimationFrame(() => focusError(form.current));
        } else if (exception.status === 409) setConflict(true);
      }
      if (!explained) setError(errorMessage(exception));
      sending.current = false;
      setPending(false);
      return;
    }
    // The POST is committed. Every retry from this point only reloads data.
    flushSync(() => {
      setCommitted(true);
      setHistory({ past: [], future: [] });
      setEditor(null);
    });
    sending.current = false;
    await refresh();
  }
  const group = data.sets.find((group) => group.key === section);
  const title = editor
    ? `${editor.remove ? 'Usuń' : editor.adding ? 'Dodaj' : 'Edytuj'} ${nouns[editor.section]}`
    : '';
  const errors = [...new Set([error, ...data.errors, ...(group?.errors || [])].filter(Boolean))];
  return (
    <>
      <div className="tasks-modal__body work-configuration space-settings-table-body">
        {refreshError ? (
          <div className="tasks-modal__errors" role="alert">
            {refreshError}
            <button
              type="button"
              className="btn btn-secondary"
              disabled={pending}
              onClick={() => void refresh()}
            >
              Spróbuj ponownie
            </button>
          </div>
        ) : null}
        {!editor &&
          errors.map((message, index) => (
            <p className="tasks-modal__errors" role="alert" key={index}>
              {message}
            </p>
          ))}
        {conflict ? (
          <p className="tasks-modal__errors" role="alert">
            Wybierz „Anuluj”, aby odrzucić szkic i pobrać aktualną konfigurację.
          </p>
        ) : null}
        {group ? (
          <section
            className="work-configuration-section"
            id={`space-settings-panel-${group.key}`}
            aria-label={group.title}
            data-configuration-section={group.key}
          >
            <div
              className="space-settings-panel"
              id={section === 'statuses' ? 'workflow-view-panel' : undefined}
              role={section === 'statuses' ? 'tabpanel' : undefined}
              aria-labelledby={section === 'statuses' ? `workflow-tab-${workflowView}` : undefined}
            >
              {section === 'statuses' && workflowView === 'map' ? (
                <WorkflowBoard
                  data={data}
                  group={group}
                  pending={blocked}
                  onChange={change}
                  onAdd={add}
                  onEdit={(index) => open({ section, index })}
                  history={{
                    canUndo: !!history.past.length && !conflict,
                    canRedo: !!history.future.length && !conflict,
                    onUndo: () => travel('undo'),
                    onRedo: () => travel('redo'),
                  }}
                  actions={{
                    dirty,
                    statusText: refreshError
                      ? 'Zmiany zapisano — odśwież widok'
                      : committed
                        ? 'Zmiany zapisano — odświeżanie…'
                        : pending
                          ? 'Zapisywanie…'
                          : dirty
                            ? 'Niezapisane zmiany'
                            : 'Wszystkie zmiany zapisane',
                    saveDisabled: conflict,
                    cancelDisabled: blocked,
                    onSave: () => void save(),
                    onCancel: () => void cancel(),
                  }}
                />
              ) : (
                <ConfigurationTable
                  key={group.key}
                  group={group}
                  pending={blocked}
                  onAdd={() => add()}
                  onEdit={(index) => open({ section, index })}
                  onRemove={remove}
                  actions={{
                    dirty,
                    saveDisabled: conflict,
                    cancelDisabled: blocked,
                    onSave: () => void save(),
                    onCancel: () => void cancel(),
                  }}
                />
              )}
            </div>
          </section>
        ) : null}
      </div>
      {editor ? (
        <Modal
          title={title}
          className={editor.remove ? 'work-modal app-modal-panel--compact' : 'work-modal'}
          hostId={hostId}
          dirty={editor.dirty}
          pending={pending}
          onClose={() => void closeEditor()}
        >
          <form
            ref={form}
            className="tasks-modal__form"
            noValidate
            onSubmit={stage}
            onChange={() => setEditor((current) => (current ? { ...current, dirty: true } : null))}
            onInput={() => setEditor((current) => (current ? { ...current, dirty: true } : null))}
          >
            <div
              className={
                editor.remove
                  ? 'tasks-modal__body'
                  : editor.section === 'types'
                    ? 'tasks-modal__body profile-edit-body space-settings-main app-form-avatar-layout work-type-form'
                    : 'tasks-modal__body documents-form resources-form'
              }
            >
              {[...new Set([...errors, ...editor.errors])].map((message, index) => (
                <p className="tasks-modal__errors" role="alert" tabIndex={-1} key={index}>
                  {message}
                </p>
              ))}
              {editor.remove ? (
                <p>
                  Usunąć pozycję „
                  {
                    editor.schema.fields.find((field) => configurationFieldName(field) === 'label')
                      ?.value
                  }
                  ”?
                  {data.shared
                    ? ' Zmiana obejmie wszystkie przestrzenie korzystające z tej konfiguracji.'
                    : ''}
                </p>
              ) : (
                <fieldset className="resources-react-fieldset" disabled={pending}>
                  {editor.section === 'types' ? (
                    <TypeFields schema={editor.schema} iconDefaults={data.type_icon_defaults} />
                  ) : (
                    <WorkflowStageFields
                      schema={editor.schema}
                      data={data}
                      adding={editor.adding}
                    />
                  )}
                </fieldset>
              )}
            </div>
            <footer className="tasks-modal__footer">
              <button
                type="button"
                className="btn btn-secondary"
                disabled={pending}
                onClick={(event) => {
                  const modal = event.currentTarget.closest<HTMLElement>('.tasks-modal');
                  if (modal) window.AncoreTaskModals?.close(modal);
                }}
              >
                Anuluj
              </button>
              <button type="submit" className="tasks-modal__submit" disabled={pending}>
                {editor.remove ? 'Usuń' : editor.adding ? 'Dodaj' : 'Zastosuj'}
              </button>
            </footer>
          </form>
        </Modal>
      ) : null}
    </>
  );
}

export default function ConfigurationPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as ConfigurationData;
  return (
    <SettingsPage
      api={initial.api_url}
      csrfToken={csrfToken}
      spaceUrl={data.space_url}
      initialTab={data.section === 'statuses' ? 'statuses' : 'types'}
      initialConfiguration={initial}
    />
  );
}
