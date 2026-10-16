import { useEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { pageRequest, type PageProps } from '../shared/page';
import PresenceSelect, { PresenceIcon } from './PresenceSelect';
import ProfileEditor from './ProfileEditor';
import type { ProfileData } from './types';

export default function ProfilePage({ initial, csrfToken }: PageProps) {
  const data = initial.data as ProfileData,
    user = data.user;
  const [editor, setEditor] = useState<'fields' | 'avatar' | null>(
    data.form.bound ? 'fields' : null,
  );
  const [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const sending = useRef(false),
    [life] = useState(() => new AbortController());
  const alert = useRef<HTMLDivElement>(null);
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    if (error) alert.current?.focus();
  }, [error]);
  async function action(url: string, body: Record<string, string>) {
    if (sending.current) return;
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const result = await pageRequest<{ redirect: string }>(
        initial.api_url,
        url,
        csrfToken,
        life.signal,
        body,
      );
      location.assign(result.redirect);
    } catch (e) {
      if (life.signal.aborted) return;
      setError(errorMessage(e));
      sending.current = false;
      setPending(false);
    }
  }
  const details = [
    [
      'Dostęp',
      user.active ? 'Aktywne' : 'Nieaktywne',
      'profile-account-access' + (user.active ? ' is-active' : ''),
    ],
    ['Rola', user.role],
    ['Dołączono', user.joined],
    ['Ostatnie logowanie', user.last_login, 'tasks-issue-muted'],
    ['Email', user.email],
    ['ID Ancore', user.username],
    ['Telefon', user.phone_number || 'Nie podano', 'tasks-issue-muted'],
    ['Stanowisko', user.job_title || 'Nie podano', 'tasks-issue-muted'],
  ];
  return (
    <div
      className="profile-page tasks-page tasks-issue-page"
      data-react-screen="account-profile"
      aria-labelledby="profile-title"
      aria-busy={pending}
    >
      <div className="tasks-issue-shell profile-issue-shell">
        <header className="tasks-issue-header">
          <div className="tasks-issue-breadcrumb">
            <span className="tasks-issue-crumb tasks-issue-crumb--current">
              <span id="profile-title">Profil użytkownika</span>
            </span>
          </div>
          <div className="tasks-issue-actions">
            <Dropdown
              label="Opcje profilu"
              searchable={false}
              disabled={pending}
              className="contacts-actions-menu"
              triggerClassName="tasks-icon-button contacts-actions-menu__toggle"
              menuClass="contacts-actions-menu__panel"
              trigger={<Icon name="ellipsis" />}
            >
              {(close) => (
                <button
                  type="button"
                  className="contacts-actions-menu__item"
                  role="menuitem"
                  onClick={() => {
                    close();
                    setEditor('fields');
                  }}
                >
                  <Icon name="pencil" />
                  Edytuj
                </button>
              )}
            </Dropdown>
          </div>
        </header>
        {error ? (
          <div ref={alert} className="tasks-error-banner" role="alert" tabIndex={-1}>
            {error}
          </div>
        ) : null}
        <main className="tasks-issue-main profile-issue-main">
          <section className="tasks-issue-content profile-issue-content" aria-label="Dane profilu">
            <div className="profile-detail-form profile-summary">
              <div className="profile-title-area profile-summary-area">
                <div className="profile-photo-control profile-photo-control--static">
                  <button
                    type="button"
                    className="profile-photo-preview-button"
                    disabled={pending}
                    aria-label="Zmień awatar użytkownika"
                    title="Zmień awatar użytkownika"
                    onClick={() => setEditor('avatar')}
                  >
                    <Avatar data={user.avatar} className="profile-page-avatar" />
                  </button>
                </div>
                <div className="profile-title-fields">
                  <div
                    className="tasks-issue-title-field profile-name-fields profile-display-name-fields"
                    aria-label="Imię, drugie imię i nazwisko"
                  >
                    {[user.first_name, user.middle_name, user.last_name].some(Boolean) ? (
                      [user.first_name, user.middle_name, user.last_name].map((name, i) =>
                        name ? (
                          <strong key={i} className="profile-display-name">
                            {name}
                          </strong>
                        ) : null,
                      )
                    ) : (
                      <strong className="profile-display-name">Nie podano</strong>
                    )}
                  </div>
                  <div className="profile-stacked-field profile-bio-field">
                    <span className="profile-field-label">Bio</span>
                    <strong className="profile-display-value profile-display-bio react-profile-bio">
                      {user.bio || 'Nie podano'}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
            <section
              className="tasks-issue-activity profile-accounts-activity"
              id="accounts"
              aria-label="Konta w sesji"
            >
              <div className="tasks-issue-activity-head">
                <h2>
                  <Icon name="users" />
                  Konta w sesji
                </h2>
                <a
                  href={data.urls.add_account}
                  className="tasks-issue-activity-chip profile-add-chip"
                >
                  <span>Dodaj konto</span>
                  <Icon name="plus" />
                </a>
              </div>
              <div className="tasks-issue-feed profile-account-feed">
                {data.accounts.map((account) => (
                  <article
                    key={account.id}
                    className={
                      'tasks-issue-feed-item profile-account-feed-item' +
                      (account.current ? ' is-current' : '')
                    }
                  >
                    <Avatar data={account.avatar} className="tasks-issue-avatar" />
                    <div className="tasks-issue-feed-body profile-account-feed-body">
                      <p>
                        <strong>{account.name}</strong>{' '}
                        <time>{account.current ? 'aktywne teraz' : 'dodane do przełącznika'}</time>
                      </p>
                      <div className="profile-account-line">
                        {account.username} · {account.email}
                      </div>
                      <span
                        className={'profile-presence-badge presence-' + account.presence_status}
                      >
                        <PresenceIcon value={account.presence_status} />
                        {account.presence_label}
                      </span>
                      <div className="profile-account-actions">
                        {account.current ? (
                          <span className="profile-current-badge">Teraz</span>
                        ) : (
                          <button
                            type="button"
                            className="profile-inline-button"
                            disabled={pending}
                            onClick={() =>
                              void action(data.urls.switch_account, { user_id: account.id })
                            }
                          >
                            Przełącz
                          </button>
                        )}
                        <button
                          type="button"
                          className="profile-icon-button"
                          disabled={pending}
                          aria-label={'Usuń konto z przełącznika: ' + account.email}
                          title="Usuń konto z przełącznika"
                          onClick={() =>
                            void action(data.urls.remove_account, { user_id: account.id })
                          }
                        >
                          <Icon name="trash-2" />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </section>
          <aside
            className="tasks-issue-sidebar profile-issue-sidebar"
            aria-label="Szczegóły profilu"
          >
            <section className="tasks-issue-side-section">
              <div className="tasks-issue-field profile-status-side-field">
                <span>Status</span>
                <div className="profile-side-status-form">
                  <PresenceSelect
                    side
                    value={user.presence_status}
                    choices={
                      data.form.fields.find((field) => field.name === 'presence_status')!.choices ||
                      []
                    }
                    disabled={pending}
                    onChange={(value) =>
                      void action(data.urls.update_presence_status, { presence_status: value })
                    }
                  />
                </div>
              </div>
              {details.map(([label, value, className]) => (
                <div className="tasks-issue-field" key={label}>
                  <span>{label}</span>
                  <strong className={className}>{value}</strong>
                </div>
              ))}
            </section>
          </aside>
        </main>
      </div>
      {editor ? (
        <ProfileEditor
          data={data}
          api={initial.api_url}
          token={csrfToken}
          avatar={editor === 'avatar'}
          onClose={() => setEditor(null)}
        />
      ) : null}
    </div>
  );
}
