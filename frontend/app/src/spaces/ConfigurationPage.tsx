import { type FormEvent, useEffect, useRef, useState } from 'react';
import { FormFields, type FormSchema } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { type Page, type PageProps, navigate, pageRequest, PageError } from '../shared/page';
import { errorMessage } from '../shared/api';
import { useDirtyGuard } from '../shared/useDirtyGuard';
interface Data {
  name: string;
  shared: boolean;
  spaces_count: number;
  space_url: string;
  revision: string;
  errors: string[];
  sets: { title: string; management: FormSchema; errors: string[]; forms: FormSchema[] }[];
}
export default function ConfigurationPage({ initial, csrfToken }: PageProps) {
  const [data, setData] = useState(initial.data as Data),
    [dirty, setDirty] = useState(false),
    [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const form = useRef<HTMLFormElement>(null),
    life = useRef(new AbortController()),
    sending = useRef(false),
    allowLeave = useDirtyGuard(dirty, pending);
  useEffect(() => () => life.current.abort(), []);
  async function save(event: FormEvent) {
    event.preventDefault();
    if (sending.current) return;
    const values = new FormData(form.current!);
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const response = await pageRequest<{ redirect?: string }>(
        initial.api_url,
        initial.url,
        csrfToken,
        life.current.signal,
        values,
      );
      allowLeave();
      navigate(response.redirect || data.space_url + '?view=settings');
    } catch (exception) {
      if (life.current.signal.aborted) return;
      if (exception instanceof PageError) {
        const response = exception.data as unknown as Page;
        if (response.type === 'space-configuration') setData(response.data as Data);
      }
      setError(errorMessage(exception));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  return (
    <div className="tasks-page tasks-list-page work-page" data-react-screen="space-configuration">
      <section className="tasks-workspace">
        <header className="tasks-topbar tasks-topbar--directory tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <a
              href={data.space_url + '?view=settings'}
              className="tasks-issue-close"
              aria-label="Wróć do ustawień"
            >
              <Icon name="arrow-left" />
            </a>
            <h1 className="tasks-topbar-title">Statusy, typy i pola</h1>
          </div>
        </header>
        <div className="work-content">
          <form
            ref={form}
            method="post"
            className="work-configuration"
            onSubmit={save}
            onChange={() => setDirty(true)}
            onInput={() => setDirty(true)}
            aria-busy={pending}
          >
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
            <div className="work-toolbar">
              <button type="submit" className="btn btn-primary" disabled={pending}>
                {pending ? 'Zapisywanie…' : 'Zapisz konfigurację'}
              </button>
              <a className="btn btn-secondary" href={data.space_url + '?view=settings'}>
                Anuluj
              </a>
            </div>
          </form>
        </div>
      </section>
    </div>
  );
}
