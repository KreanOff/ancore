import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { FieldControl, type FormSchema } from '../forms/FormDialog';
import { Modal } from '../shared/Modal';
import SettingsPage from './SettingsPage';
import ConfigurationTable from './ConfigurationTable';
import TypeFields from './TypeFields';
import {
  configurationEditorSchema,
  configurationFieldName,
  configurationHasRow,
  configurationAdd,
  configurationDraftKey,
  configurationDraftSubmission,
  configurationRemove,
  configurationMove,
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
const nouns = { types: 'typ zgłoszenia', statuses: 'status', fields: 'pole dodatkowe' };
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
}: PageProps & {
  onSaved: () => Promise<void>;
  onCancel?: () => void;
  onStateChange: (dirty: boolean, pending: boolean) => void;
  hostId?: string;
  section?: 'types' | 'statuses';
}) {
  const [baseline, setBaseline] = useState(initial.data as ConfigurationData);
  const [data, setData] = useState(baseline);
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
  const dirty =
    !committed &&
    (untrustedBaseline || configurationDraftKey(data) !== configurationDraftKey(baseline));
  const blocked = pending || committed || !!refreshError;

  useEffect(() => {
    if (initial.data === source.current || (dirty && !committed)) return;
    source.current = initial.data;
    const clean = initial.data as ConfigurationData;
    setData(clean);
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
    setBaseline(clean);
    setUntrustedBaseline(false);
    nativeEditor.current = false;
    setEditor(null);
    setError('');
    setConflict(false);
    setCommitted(false);
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
  function add() {
    if (blocked || sending.current) return;
    try {
      const next = configurationAdd(data, section);
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
      setData(configurationRemove(data, section, indices));
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
      setData(
        editor.remove
          ? configurationRemove(data, editor.section, [editor.index])
          : configurationStage(data, editor, new FormData(form.current)),
      );
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
            <ConfigurationTable
              key={group.key}
              group={group}
              pending={blocked}
              onAdd={add}
              onEdit={(index) => open({ section, index })}
              onRemove={remove}
              onMove={
                section === 'statuses'
                  ? (index, direction) =>
                      setData(configurationMove(data, section, index, direction))
                  : undefined
              }
              actions={{
                dirty,
                saveDisabled: conflict,
                cancelDisabled: blocked,
                onSave: () => void save(),
                onCancel: () => void cancel(),
              }}
            />
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
                    <div className="app-form-layout">
                      {editor.schema.fields.map((field) => (
                        <FieldControl key={field.name} field={field} />
                      ))}
                    </div>
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
