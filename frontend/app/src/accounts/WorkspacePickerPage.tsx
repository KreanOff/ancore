import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { LoadingOverlay } from '../shared/LoadingOverlay';
import { useNativeSubmitLoading } from '../shared/useNativeSubmitLoading';
import type { PageProps } from '../shared/page';
import type { WorkspacePickerData } from './types';

export default function WorkspacePickerPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as WorkspacePickerData;
  const switching = useNativeSubmitLoading();
  return (
    <main className="auth-shell" data-react-screen="account-workspace-picker">
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
              <h1 id="auth-form-title" tabIndex={-1}>
                Wybierz Workspace
              </h1>
            </header>
            {data.workspaces.length ? (
              <ul className="auth-workspace-list">
                {data.workspaces.map((item) => (
                  <li key={item.id}>
                    <form
                      method="post"
                      action={item.switch_url}
                      onSubmit={switching.onSubmit}
                      aria-busy={switching.pending}
                    >
                      <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                      <button
                        type="submit"
                        className="auth-workspace-option"
                        disabled={switching.pending}
                      >
                        <Avatar
                          space
                          data={item.avatar}
                          className="profile-avatar--workplace workplace-row__avatar"
                        />
                        <span className="auth-workspace-name">{item.name}</span>
                        <Icon name="arrow-right" />
                      </button>
                    </form>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="auth-form-subtitle">Brak dostępnych Workspace.</p>
            )}
            <div className="auth-footer auth-footer--workspace">
              <p>
                Chcesz utworzyć kolejny Workspace? <a href={data.urls.create}>Utwórz Workspace</a>
              </p>
              <form method="post" action={data.urls.logout} className="auth-logout-form">
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                Nie widzisz swojego Workspace?{' '}
                <button type="submit" className="auth-link-button">
                  Wyloguj się i zmień konto
                </button>
              </form>
            </div>
          </div>
        </section>
      </div>
      <LoadingOverlay active={switching.pending} label="Przełączanie Workspace…" />
    </main>
  );
}
