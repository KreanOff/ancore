import { useState } from 'react';
import { pageRequest, type PageProps } from '../shared/page';
import { errorMessage } from '../shared/api';

export default function JoinPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as {
    name: string;
    role: string;
    error: string;
    authenticated: boolean;
    urls: Record<string, string>;
  };
  const [pending, setPending] = useState(false),
    [error, setError] = useState(data.error);
  return (
    <main className="auth-shell" data-react-screen="account-join">
      <header className="auth-topbar">
        <a href={data.urls.home} className="auth-brand" aria-label="Ancore — strona główna">
          <span className="auth-brand-mark" aria-hidden="true" />
          <span className="auth-brand-name">ANCORE</span>
        </a>
      </header>
      <div className="auth-content">
        <section className="auth-form-panel" aria-labelledby="auth-form-title">
          <div className="auth-form-inner">
            <header className="auth-form-header">
              <h1 id="auth-form-title">Dołącz do Workspace</h1>
              <p className="auth-form-subtitle">
                {data.name} · {data.role}
              </p>
            </header>
            {error ? (
              <div className="auth-alert" role="alert">
                {error}
              </div>
            ) : data.authenticated ? (
              <form
                className="auth-form"
                method="post"
                aria-busy={pending}
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (pending) return;
                  setPending(true);
                  try {
                    const response = await pageRequest<{
                      redirect?: string;
                      data?: { error?: string };
                    }>(
                      initial.api_url,
                      initial.url,
                      csrfToken,
                      new AbortController().signal,
                      new FormData(event.currentTarget),
                    );
                    if (response.redirect) location.assign(response.redirect);
                    else {
                      setError(response.data?.error || 'Zaproszenie jest niedostępne.');
                      setPending(false);
                    }
                  } catch (reason) {
                    setError(errorMessage(reason));
                    setPending(false);
                  }
                }}
              >
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                <button className="auth-submit" type="submit" disabled={pending}>
                  {pending ? 'Dołączanie…' : 'Dołącz do Workspace'}
                </button>
              </form>
            ) : (
              <>
                <p>Zaloguj się lub utwórz konto, aby przyjąć zaproszenie.</p>
                <p>
                  <a href={data.urls.login}>Zaloguj się</a> ·{' '}
                  <a href={data.urls.register}>Utwórz konto</a>
                </p>
              </>
            )}
            {error && data.authenticated ? (
              <p>
                <a href={data.urls.profile}>Przejdź do profilu i zmień konto</a>
              </p>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
