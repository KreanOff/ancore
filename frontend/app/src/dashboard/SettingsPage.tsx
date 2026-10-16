import { useEffect, useState } from 'react';
import { Avatar, type AvatarData } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { setPageLocation } from '../shared/page';
import type { PageProps } from '../shared/page';
interface Data {
  user: { name: string; email: string; avatar: AvatarData };
  profile_url: string;
  logout_url: string;
  rows: { category: string; url: string; icon: string; title: string; description: string }[];
}
const categoryFromHash = () =>
  ['account', 'security'].includes(location.hash.slice(1))
    ? 'account'
    : location.hash === '#workspace'
      ? 'workspace'
      : 'all';
export default function SettingsPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as Data;
  const [category, setCategory] = useState(categoryFromHash);
  useEffect(() => {
    const controller = new AbortController();
    const sync = () => setCategory(categoryFromHash());
    window.addEventListener('hashchange', sync, { signal: controller.signal });
    window.addEventListener('popstate', sync, { signal: controller.signal });
    const click = (event: MouseEvent) => {
      const target = (event.target as Element).closest<HTMLAnchorElement>(
        '[data-sidebar-navigation="settings"] [data-settings-category]',
      );
      if (!target || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
      event.preventDefault();
      const next = target.dataset.settingsCategory || 'all';
      setPageLocation(
        location.pathname + location.search + (next === 'all' ? '' : `#${next}`),
        true,
      );
      setCategory(next);
      window.dispatchEvent(new CustomEvent('ancore:settings-category'));
      document.querySelector('.settings-scroll-area')?.scrollTo({ top: 0 });
    };
    document.addEventListener('click', click, { signal: controller.signal, capture: true });
    return () => controller.abort();
  }, []);
  return (
    <div className="dashboard-page settings-center" data-react-screen="settings">
      <header className="tasks-topbar tasks-topbar--project-directory">
        <div className="tasks-titlebar-left">
          <h1 className="tasks-topbar-title" id="settings-title">
            Ustawienia
          </h1>
        </div>
      </header>
      <div className="settings-scroll-area">
        <div className="settings-layout">
          <div className="settings-content" aria-labelledby="settings-title">
            {category !== 'workspace' ? (
              <div className="settings-account-summary">
                <Avatar data={data.user.avatar} className="settings-account-avatar" />
                <div className="settings-account-copy">
                  <strong>{data.user.name}</strong>
                  <span>{data.user.email}</span>
                </div>
                <a className="settings-button" href={data.profile_url}>
                  Edytuj profil
                </a>
              </div>
            ) : null}
            {(
              [
                ['account', 'Konto i dostęp', 'Dane osobowe i konta, z których korzystasz.'],
                ['workspace', 'Workspace', 'Organizacja pracy, przestrzenie, pulpity i filtry.'],
              ] as const
            )
              .filter(([key]) => category === 'all' || category === key)
              .map(([key, label, description]) => (
                <section key={key} className="settings-group" id={key}>
                  <header className="settings-group-heading">
                    <h2>{label}</h2>
                    <p>{description}</p>
                  </header>
                  <div className="settings-rows">
                    {data.rows
                      .filter((row) => row.category === key)
                      .map((row) => (
                        <a key={row.url} className="settings-row settings-row--link" href={row.url}>
                          <span className="settings-row-icon">
                            <Icon name={row.icon} />
                          </span>
                          <span className="settings-row-copy">
                            <strong>{row.title}</strong>
                            <span>{row.description}</span>
                          </span>
                          <span className="settings-row-arrow">
                            <Icon name="chevron-right" />
                          </span>
                        </a>
                      ))}
                  </div>
                </section>
              ))}
            {category !== 'workspace' ? (
              <section
                className="settings-session"
                id="security"
                aria-label="Sesja i bezpieczeństwo"
              >
                <div className="settings-row">
                  <span className="settings-row-icon">
                    <Icon name="shield-check" />
                  </span>
                  <div className="settings-row-copy">
                    <strong>Sesja</strong>
                    <span>Zalogowano jako {data.user.email}</span>
                  </div>
                  <form method="post" action={data.logout_url}>
                    <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken} />
                    <button type="submit" className="settings-button">
                      Wyloguj się
                    </button>
                  </form>
                </div>
              </section>
            ) : null}
            <span className="u-sr-only" role="status" aria-live="polite">
              Liczba widocznych ustawień:{' '}
              {data.rows.filter((row) => category === 'all' || row.category === category).length}.
            </span>
          </div>
        </div>
        <p className="icon-credit">
          Ikony UIcons:{' '}
          <a href="https://www.flaticon.com/uicons" target="_blank" rel="noopener noreferrer">
            Flaticon
          </a>
        </p>
      </div>
    </div>
  );
}
