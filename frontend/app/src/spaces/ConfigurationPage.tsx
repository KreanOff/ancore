import { type FormEvent, useEffect, useRef, useState } from 'react';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import SettingsDialog from './SettingsDialog';
import { type Page, type PageProps, pageRequest, PageError } from '../shared/page';
import { errorMessage } from '../shared/api';
import { navigate } from '../shared/page';
export interface ConfigurationData {
  name: string;
  shared: boolean;
  spaces_count: number;
  space_url: string;
  revision: string;
  errors: string[];
  sets: { title: string; management: FormSchema; errors: string[]; forms: FormSchema[] }[];
}
export function ConfigurationForm({
  initial,
  csrfToken,
  onSaved,
  onStateChange,
}: PageProps & {
  onSaved: () => Promise<void>;
  onStateChange: (dirty: boolean, pending: boolean) => void;
}) {
  const [data, setData] = useState(initial.data as ConfigurationData),
    [dirty, setDirty] = useState(false),
    [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const form = useRef<HTMLFormElement>(null),
    life = useRef(new AbortController()),
    sending = useRef(false);
  useEffect(() => onStateChange(dirty, pending), [dirty, pending, onStateChange]);
  useEffect(() => () => life.current.abort(), []);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const values = new FormData(form.current!);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      await pageRequest<{ redirect?: string }>(
        initial.api_url,
        initial.url,
        csrfToken,
        life.current.signal,
        values,
      );
      setDirty(false);
      await onSaved();
    } catch (exception) {
      if (life.current.signal.aborted) return;
      if (exception instanceof PageError) {
        const response = exception.data as unknown as Page;
        if (response.type === 'space-configuration') setData(response.data as ConfigurationData);
      }
      setError(errorMessage(exception));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <form
      ref={form}
      method="post"
      className="tasks-modal__form"
      onSubmit={save}
      onChange={() => setDirty(true)}
      onInput={() => setDirty(true)}
      aria-busy={pending}
    >
      <div className="tasks-modal__body work-configuration">
        <input type="hidden" name="revision" value={data.revision} />
        <p>
          Konfiguracja: {data.name}
          {data.shared
            ? ` · Wspólna dla ${data.spaces_count} przestrzeni. Zapis zmieni wszystkie korzystające z niej przestrzenie.`
            : ' · Niezależna konfiguracja przestrzeni.'}
        </p>
        {error ? (
          <p className="tasks-modal__errors" role="alert">
            {error}
          </p>
        ) : null}
        {data.errors.map((message, index) => (
          <p className="tasks-modal__errors" role="alert" key={index}>
            {message}
          </p>
        ))}
        <fieldset className="resources-react-fieldset" disabled={pending}>
          {data.sets.map((group) => (
            <section className="work-panel" key={group.title}>
              <h2>{group.title}</h2>
              <p className="work-caption">
                Aby dodać pozycję, wypełnij pusty wiersz. Kolejny pojawi się po zapisie.
              </p>
              <FormFields schema={group.management} />
              {group.errors.map((message, index) => (
                <p className="tasks-modal__errors" role="alert" key={index}>
                  {message}
                </p>
              ))}
              {group.forms.map((schema, index) => (
                <div className="work-configuration-row" key={index}>
                  <FormFields schema={schema} />
                </div>
              ))}
            </section>
          ))}
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
          Anuluj
        </button>
        <button type="submit" className="tasks-modal__submit" disabled={pending}>
          {pending ? 'Zapisywanie…' : 'Zapisz konfigurację'}
        </button>
      </footer>
    </form>
  );
}

export default function ConfigurationPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as ConfigurationData;
  return (
    <SettingsDialog
      api={initial.api_url}
      csrfToken={csrfToken}
      spaceUrl={data.space_url}
      initialTab="configuration"
      initialConfiguration={initial}
      onClose={() => navigate(data.space_url)}
      onSaved={() => navigate(data.space_url)}
    />
  );
}
