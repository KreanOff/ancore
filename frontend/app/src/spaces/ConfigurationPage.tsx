import { type FormEvent, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import { Modal } from '../shared/Modal';
import SettingsPage from './SettingsPage';
import ConfigurationTable from './ConfigurationTable';
import {
  configurationEditorSchema,
  configurationFieldName,
  configurationHasRow,
  configurationSubmission,
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
}
interface EditorState extends ConfigurationEditor {
  schema: FormSchema;
  errors: string[];
  dirty: boolean;
  adding: boolean;
}
const nouns = { types: 'typ zgłoszenia', statuses: 'status', fields: 'pole dodatkowe' };
function createEditor(data: ConfigurationData, selection: ConfigurationEditor): EditorState | null {
  if (selection.section !== 'types') return null;
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
  onCancel,
  hostId,
}: PageProps & {
  onSaved: () => Promise<void>;
  onCancel?: () => void;
  onStateChange: (dirty: boolean, pending: boolean) => void;
  hostId?: string;
}) {
  const section = 'types';
  const [data, setData] = useState(initial.data as ConfigurationData);
  const [editor, setEditor] = useState<EditorState | null>(() =>
    data.editor ? createEditor(data, data.editor) : null,
  );
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [refreshError, setRefreshError] = useState('');
  const [life] = useState(() => new AbortController());
  const form = useRef<HTMLFormElement>(null);
  const sending = useRef(false);
  // Modal owns draft protection. Parent only blocks navigation while saving.
  useEffect(() => setData(initial.data as ConfigurationData), [initial.data]);
  useEffect(() => onStateChange(false, pending), [pending, onStateChange]);
  useEffect(() => () => life.abort(), [life]);
  async function closeEditor() {
    if (pending || sending.current) return;
    const boundInitial =
      data.editor && data.sets.some((group) => group.forms.some((schema) => schema.bound));
    if (!boundInitial) {
      setEditor(null);
      setError('');
      return;
    }
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
      if (!life.signal.aborted) {
        setData(clean.data as ConfigurationData);
        setEditor(null);
        setError('');
      }
    } catch (exception) {
      if (!life.signal.aborted)
        setError('Nie udało się odrzucić zmian i odświeżyć listy. ' + errorMessage(exception));
    } finally {
      if (!life.signal.aborted) setPending(false);
    }
  }
  async function refresh() {
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
      if (!life.signal.aborted) setPending(false);
    }
  }
  function open(selection: ConfigurationEditor) {
    if (pending || refreshError) return;
    setError('');
    setEditor(createEditor(data, selection));
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current || !editor || !form.current) return;
    if (!editor.remove && !form.current.reportValidity()) return;
    const values = configurationSubmission(data, editor, new FormData(form.current));
    sending.current = true;
    setPending(true);
    setError('');
    try {
      await pageRequest(
        initial.api_url,
        data.space_url + 'configuration/',
        csrfToken,
        life.signal,
        values,
      );
    } catch (exception) {
      if (life.signal.aborted) return;
      if (exception instanceof PageError) {
        const response = exception.data as unknown as Page;
        if (response.type === 'space-configuration') {
          const corrected = response.data as ConfigurationData;
          const row = corrected.sets.find((group) => group.key === editor.section)?.forms[
            editor.index
          ];
          const group = corrected.sets.find((group) => group.key === editor.section);
          if (row && group) {
            flushSync(() => {
              setPending(false);
              setEditor({
                ...editor,
                schema: configurationEditorSchema(row),
                errors: [...corrected.errors, ...group.errors, ...row.errors],
              });
            });
            requestAnimationFrame(() => focusError(form.current));
          }
        }
      }
      setError(errorMessage(exception));
      sending.current = false;
      setPending(false);
      return;
    }
    // The mutation succeeded. Close the draft before refreshing so a failed GET
    // offers a read retry instead of a second create/delete request.
    setEditor(null);
    sending.current = false;
    await refresh();
  }
  const group = data.sets.find((group) => group.key === section);
  const title = editor
    ? `${editor.remove ? 'Usuń' : editor.adding ? 'Dodaj' : 'Edytuj'} ${nouns[editor.section]}`
    : '';
  return (
    <>
      <div className="tasks-modal__body work-configuration">
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
              pending={pending || !!refreshError}
              onAdd={() => {
                const index = group.forms.findIndex((schema) => !configurationHasRow(schema));
                if (index >= 0) open({ section, index });
              }}
              onEdit={(index) => open({ section, index })}
              onRemove={(index) => open({ section, index, remove: true })}
            />
          </section>
        ) : null}
      </div>
      <footer className="tasks-modal__footer">
        <button type="button" className="btn btn-secondary" disabled={pending} onClick={onCancel}>
          Zamknij
        </button>
      </footer>
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
            onSubmit={save}
            onChange={() => setEditor((current) => (current ? { ...current, dirty: true } : null))}
            onInput={() => setEditor((current) => (current ? { ...current, dirty: true } : null))}
          >
            <div className="tasks-modal__body">
              {error ? (
                <p className="tasks-modal__errors" role="alert" tabIndex={-1}>
                  {error}
                </p>
              ) : null}
              {editor.errors.map((message, index) => (
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
                  <FormFields schema={editor.schema} layout />
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
                {pending ? 'Zapisywanie…' : editor.remove ? 'Usuń' : 'Zapisz'}
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
      initialTab="types"
      initialConfiguration={initial}
    />
  );
}
