import { type FormEvent, useEffect, useRef, useState } from 'react';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import { Modal } from '../shared/Modal';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { PageError, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import type { TaskData } from './types';
export interface DialogData {
  kind: 'log' | 'subtask' | 'share' | 'role';
  title: string;
  schema: FormSchema;
  action: string;
  values?: Record<string, string | number>;
  url: string;
}
export default function SchemaDialog({
  dialog,
  api,
  csrfToken,
  onClose,
  onSaved,
  returnFocus,
}: {
  dialog: DialogData;
  api: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: () => Promise<void>;
  returnFocus?: HTMLElement | null;
}) {
  const [schema, setSchema] = useState(() => ({
      ...dialog.schema,
      fields: dialog.schema.fields.map((field) =>
        dialog.values && field.name.replace(/^worklog-/, '') in dialog.values
          ? { ...field, value: String(dialog.values[field.name.replace(/^worklog-/, '')]) }
          : field,
      ),
    })),
    [dirty, setDirty] = useState(false),
    [pending, setPending] = useState(false),
    [saved, setSaved] = useState(false),
    [error, setError] = useState(''),
    [candidates, setCandidates] = useState<{ email: string; name: string; avatar: AvatarData }[]>(
      [],
    ),
    [searchStatus, setSearchStatus] = useState('');
  const form = useRef<HTMLFormElement>(null),
    life = useRef(new AbortController()),
    sending = useRef(false),
    committed = useRef(false);
  useEffect(() => () => life.current.abort(), []);
  useEffect(() => {
    if (dialog.kind !== 'share') return;
    let timer: ReturnType<typeof setTimeout>, request: AbortController | undefined;
    const element = form.current!;
    const input = element.elements.namedItem('email') as HTMLInputElement;
    function search() {
      clearTimeout(timer);
      request?.abort();
      setCandidates([]);
      if (input.value.trim().length < 2) {
        setSearchStatus('Wpisz co najmniej 2 znaki.');
        return;
      }
      setSearchStatus('Szukanie…');
      timer = setTimeout(async () => {
        request = new AbortController();
        const signal = AbortSignal.any([request.signal, life.current.signal]);
        try {
          const result = await pageRequest<{
            results: { email: string; name: string; avatar: AvatarData }[];
            has_more: boolean;
          }>(
            api,
            dialog.url + 'candidates/?q=' + encodeURIComponent(input.value.trim()),
            csrfToken,
            signal,
          );
          setCandidates(result.results);
          setSearchStatus(
            result.results.length
              ? result.has_more
                ? 'Doprecyzuj wyszukiwanie, aby zobaczyć pozostałe osoby.'
                : ''
              : 'Brak pasujących osób.',
          );
        } catch (exception) {
          if (!signal.aborted) setSearchStatus(errorMessage(exception));
        }
      }, 200);
    }
    input.addEventListener('input', search);
    return () => {
      clearTimeout(timer);
      request?.abort();
      input.removeEventListener('input', search);
    };
  }, [dialog.kind, dialog.url, api, csrfToken]);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError('');
    try {
      if (!committed.current) {
        const body = new FormData(form.current!);
        body.set('action', dialog.action);
        if (dialog.values?.id) body.set('work_log_id', String(dialog.values.id));
        await pageRequest(api, dialog.url, csrfToken, life.current.signal, body);
        committed.current = true;
        setSaved(true);
        setDirty(false);
      }
      await onSaved();
      onClose();
    } catch (exception) {
      if (life.current.signal.aborted) return;
      if (committed.current) {
        setError(
          `Zapisano zmiany, ale nie udało się odświeżyć zadania. ${errorMessage(exception)}`,
        );
        return;
      }
      if (exception instanceof PageError) {
        const data = exception.data.data as TaskData | undefined;
        if (data) setSchema(dialog.kind === 'subtask' ? data.subtask_form : data.log_form);
        else if (exception.data.errors) {
          setError(
            Object.entries(exception.data.errors as Record<string, { message: string }[]>)
              .flatMap(([key, rows]) => rows.map((row) => `${key}: ${row.message}`))
              .join(' '),
          );
          return;
        }
      }
      setError(errorMessage(exception));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  function changed(event: FormEvent) {
    setDirty(true);
    const input = event.target as HTMLInputElement;
    if (dialog.kind === 'log') {
      const mode = form.current?.elements.namedItem(
        'worklog-calculation_mode',
      ) as HTMLInputElement | null;
      if (mode) {
        if (/worklog-(hours|minutes)/.test(input.name)) mode.value = 'duration';
        else if (/worklog-(started_at|ended_at)/.test(input.name)) mode.value = 'interval';
      }
    }
  }
  return (
    <Modal
      title={dialog.title}
      size={schema.compact ? 'compact' : 'panel'}
      returnFocus={returnFocus}
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        ref={form}
        className="tasks-modal__form"
        onSubmit={save}
        onChange={changed}
        onInput={changed}
      >
        <div className="tasks-modal__body documents-form resources-form">
          {error ? (
            <p className="tasks-modal__errors resources-form-wide" role="alert">
              {error}
            </p>
          ) : null}
          {schema.errors.map((message, index) => (
            <p className="tasks-modal__errors resources-form-wide" role="alert" key={index}>
              {message}
            </p>
          ))}
          <fieldset className="resources-react-fieldset" disabled={pending || saved}>
            <FormFields schema={schema} layout />
            {dialog.kind === 'share' ? (
              <div className="resources-form-wide">
                <div
                  className="workplace-invite__results"
                  role="listbox"
                  aria-label="Osoby, którym możesz udostępnić zadanie"
                  hidden={!candidates.length}
                >
                  {candidates.map((person) => (
                    <button
                      key={person.email}
                      type="button"
                      role="option"
                      aria-selected="false"
                      className="tasks-project-menu-button"
                      onClick={() => {
                        const input = form.current!.elements.namedItem('email') as HTMLInputElement;
                        input.value = person.email;
                        setCandidates([]);
                        setSearchStatus(`Wybrano: ${person.name}`);
                        setDirty(true);
                      }}
                    >
                      <span className="tasks-responsible-select__person">
                        <Avatar data={person.avatar} className="tasks-directory-avatar" />
                        <span className="tasks-responsible-select__identity">
                          <span className="workplace-team__name">{person.name}</span>
                          <span className="workplace-team__name">{person.email}</span>
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
                <span className="workplace-team__hint" role="status">
                  {searchStatus}
                </span>
              </div>
            ) : null}
          </fieldset>
        </div>
        <footer className="tasks-modal__footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={() => {
              const modal = form.current?.closest<HTMLElement>('.tasks-modal');
              if (modal) window.AncoreTaskModals?.close(modal);
            }}
          >
            {saved ? 'Zamknij' : 'Anuluj'}
          </button>
          <button type="submit" className="tasks-modal__submit" disabled={pending}>
            {pending
              ? saved
                ? 'Odświeżanie…'
                : 'Zapisywanie…'
              : saved
                ? 'Odśwież zadanie'
                : dialog.kind === 'subtask'
                  ? 'Dodaj podzadanie'
                  : dialog.kind === 'share'
                    ? 'Udostępnij'
                    : 'Zapisz'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
