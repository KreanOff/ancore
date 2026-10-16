import { type FormEvent, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { PulpitFields } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, PageError, navigate, pageRequest } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import type { EditData } from './types';
export default function EditPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as EditData;
  const [schema, setSchema] = useState(data.form),
    [dirty, setDirty] = useState(data.form.bound),
    [pending, setPending] = useState(false),
    [error, setError] = useState(''),
    [visibility, setVisibility] = useState(
      String(data.form.fields.find((field) => field.name === 'visibility')?.value || ''),
    );
  const form = useRef<HTMLFormElement>(null),
    life = useRef(new AbortController()),
    sending = useRef(false);
  useDirtyGuard(dirty, pending);
  useLayoutEffect(() => {
    if (form.current) window.AncoreCustomSelect?.refresh(form.current);
  }, [schema, visibility]);
  useEffect(() => {
    const element = form.current!;
    const changed = (event: Event) => {
      setDirty(true);
      if (event.target instanceof HTMLSelectElement && event.target.name === 'visibility')
        setVisibility(event.target.value);
    };
    element.addEventListener('input', changed);
    element.addEventListener('change', changed);
    return () => {
      life.current.abort();
      element.removeEventListener('input', changed);
      element.removeEventListener('change', changed);
    };
  }, []);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const values = new FormData(form.current!);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        initial.api_url,
        data.action,
        csrfToken,
        life.current.signal,
        values,
      );
      if (life.current.signal.aborted) return;
      flushSync(() => {
        setDirty(false);
        setPending(false);
      });
      await navigate(result.redirect);
    } catch (exception) {
      if (life.current.signal.aborted) return;
      if (exception instanceof PageError) {
        const corrected = (exception.data as unknown as Page).data as EditData | undefined;
        if (corrected?.form) {
          setSchema(corrected.form);
          setVisibility(
            String(corrected.form.fields.find((field) => field.name === 'visibility')?.value || ''),
          );
        }
      }
      setError(errorMessage(exception));
      requestAnimationFrame(() => {
        const invalid = form.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
        (
          invalid?.closest('.ancore-custom-select')?.querySelector<HTMLElement>('button') || invalid
        )?.focus();
      });
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <div
      className="tasks-container work-page work-page--management pulpits-page pulpit-edit-page"
      data-react-screen="pulpit-edit"
    >
      <section className="tasks-workspace">
        <header className="tasks-topbar tasks-topbar--directory pulpit-topbar">
          <div className="tasks-titlebar-left">
            <h1 className="tasks-topbar-title" title={initial.title}>
              {initial.title}
            </h1>
          </div>
          <div className="tasks-titlebar-actions">
            <a className="tasks-tag-topbar-button" href={data.dashboard.url}>
              <Icon name="eye" />
              <span>Wyświetl pulpit</span>
            </a>
          </div>
        </header>
        <div className="work-content pulpit-edit-content">
          <form
            ref={form}
            className="documents-form pulpit-form pulpit-edit-form"
            action={data.action}
            onSubmit={save}
            aria-busy={pending}
            aria-label={data.section === 'access' ? 'Dostępy pulpitu' : 'Ustawienia pulpitu'}
          >
            {error ? (
              <div className="tasks-modal__errors" role="alert">
                {error}
              </div>
            ) : null}
            {schema.errors.length ? (
              <div className="tasks-modal__errors" role="alert">
                {schema.errors.map((message, index) => (
                  <p key={index}>{message}</p>
                ))}
              </div>
            ) : null}
            <fieldset className="resources-react-fieldset" disabled={pending}>
              <PulpitFields schema={schema} visibility={visibility} />
            </fieldset>
            <div className="pulpit-edit-actions">
              <a href={data.return_url} className="btn btn-secondary">
                Anuluj
              </a>
              <button type="submit" className="btn btn-primary" disabled={pending}>
                {pending ? 'Zapisywanie…' : 'Zapisz'}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
