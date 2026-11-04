import { useEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { copyText } from '../shared/clipboard';
import { pageRequest, type PageProps } from '../shared/page';
import PresenceSelect, { PresenceIcon } from './PresenceSelect';
import ProfileEditor from './ProfileEditor';
import BannerEditor from './BannerEditor';
import { bannerCropStyle } from './banner-crop';
import type { ProfileData } from './types';

export default function ProfilePage({ initial, csrfToken }: PageProps) {
  const data = initial.data as ProfileData,
    user = data.user;
  const [editor, setEditor] = useState<'fields' | 'avatar' | 'banner' | null>(
    data.banner_form.bound ? 'banner' : data.form.bound ? 'fields' : null,
  );
  const [focusField, setFocusField] = useState<string>();
  const [copied, setCopied] = useState('');
  const [copyError, setCopyError] = useState('');
  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(''), 2500);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const edit = (field?: string) => {
    setFocusField(field);
    setEditor('fields');
  };
  async function copy(value: string, label: string) {
    setCopyError('');
    setCopied('');
    try {
      await copyText(value);
      if (!life.signal.aborted) setCopied(label);
    } catch {
      if (!life.signal.aborted)
        setCopyError('Nie udało się skopiować danych. Zaznacz tekst i skopiuj go ręcznie.');
    }
  }
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
  const accountDetails = [
    [
      'Dostęp',
      user.active ? 'Aktywny' : 'Nieaktywny',
      'profile-account-access' + (user.active ? ' is-active' : ''),
    ],
    ['Rola w aplikacji', user.role],
    ['Dołączono', user.joined],
    ['Ostatnie logowanie', user.last_login, 'tasks-issue-muted'],
  ];
  const contactDetails = [
    {
      label: 'E-mail',
      value: user.email,
      icon: 'mail',
      href: `mailto:${user.email}`,
      field: 'email',
    },
    { label: 'ID Ancore', value: user.username, icon: 'circle-user-round', field: 'username' },
    {
      label: 'Telefon',
      value: user.phone_number,
      icon: 'phone',
      href: `tel:${user.phone_number.replace(/[^+\d]/g, '')}`,
      field: 'phone_number',
    },
  ];
  const suggestions = [
    {
      field: 'job_title',
      value: user.job_title,
      icon: 'briefcase',
      label: 'Dodaj stanowisko',
      description: 'Czym zajmujesz się na co dzień?',
    },
    {
      field: 'bio',
      value: user.bio,
      icon: 'user-round',
      label: 'Napisz kilka słów o sobie',
      description: 'Podziel się swoim doświadczeniem i zainteresowaniami.',
    },
    {
      field: 'phone_number',
      value: user.phone_number,
      icon: 'phone',
      label: 'Dodaj numer telefonu',
      description: 'Ułatw kontakt ze sobą.',
    },
  ].filter((item) => !item.value.trim());
  const presenceChoices =
    data.form.fields.find((field) => field.name === 'presence_status')?.choices || [];
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
            <h1 className="tasks-issue-crumb tasks-issue-crumb--current" id="profile-title">
              Profil użytkownika
            </h1>
          </div>
          <div className="tasks-issue-actions">
            <button
              type="button"
              className="tasks-filter-button"
              disabled={pending}
              onClick={() => edit()}
            >
              <Icon name="pencil" />
              Edytuj profil
            </button>
          </div>
        </header>
        {error ? (
          <div ref={alert} className="tasks-error-banner" role="alert" tabIndex={-1}>
            {error}
          </div>
        ) : null}
        <main className="tasks-issue-main profile-issue-main profile-overview">
          <div className="profile-overview-inner">
            <section className="profile-hero profile-summary" aria-label="Dane profilu">
              <div className="profile-banner">
                <img
                  className="profile-banner-image"
                  src={data.banner.url}
                  alt=""
                  style={bannerCropStyle(data.banner.crop)}
                />
                <button
                  type="button"
                  className="tasks-filter-button profile-banner-action"
                  disabled={pending}
                  onClick={() => setEditor('banner')}
                >
                  <Icon name="image" />
                  Zmień baner
                </button>
              </div>
              <div className="profile-hero-identity">
                <button
                  type="button"
                  className="profile-photo-preview-button profile-hero-avatar"
                  disabled={pending}
                  aria-label="Zmień awatar użytkownika"
                  title="Zmień awatar użytkownika"
                  onClick={() => setEditor('avatar')}
                >
                  <Avatar data={user.avatar} className="profile-page-avatar" />
                  <span className="profile-avatar-edit" aria-hidden="true">
                    <Icon name="image" />
                  </span>
                </button>
                <div className="profile-title-fields">
                  <h2 className="profile-display-name">{user.name}</h2>
                  <div className="profile-identity-line">
                    <span className="profile-identity-handle">{user.username}</span>
                    <span className={'profile-presence-badge presence-' + user.presence_status}>
                      <PresenceIcon value={user.presence_status} />
                      {
                        presenceChoices.find((choice) => choice.value === user.presence_status)
                          ?.label
                      }
                    </span>
                  </div>
                  {user.job_title ? (
                    <p className="profile-hero-job">
                      <Icon name="briefcase" />
                      {user.job_title}
                    </p>
                  ) : (
                    <button
                      type="button"
                      className="profile-text-action"
                      disabled={pending}
                      onClick={() => edit('job_title')}
                    >
                      <Icon name="plus" />
                      Dodaj stanowisko
                    </button>
                  )}
                </div>
              </div>
            </section>
            <div className="profile-details-grid">
              <div className="profile-about-column">
                <section
                  className="profile-overview-card profile-about"
                  aria-labelledby="profile-bio-title"
                >
                  <div className="profile-section-heading">
                    <h2 className="profile-section-title" id="profile-bio-title">
                      <Icon name="user-round" />O mnie
                    </h2>
                    <button
                      type="button"
                      className="tasks-filter-button profile-icon-action"
                      aria-label="Edytuj opis"
                      title="Edytuj opis"
                      disabled={pending}
                      onClick={() => edit('bio')}
                    >
                      <Icon name="pencil" />
                    </button>
                  </div>
                  {user.bio.trim() ? (
                    <p className="profile-display-value profile-display-bio react-profile-bio">
                      {user.bio}
                    </p>
                  ) : (
                    <div className="profile-bio-empty">
                      <p className="profile-empty-title">Daj się poznać</p>
                      <p>Opowiedz, czym się zajmujesz, co Cię interesuje i w czym możesz pomóc.</p>
                      <button
                        type="button"
                        className="tasks-filter-button"
                        disabled={pending}
                        onClick={() => edit('bio')}
                      >
                        <Icon name="plus" />
                        Dodaj opis
                      </button>
                    </div>
                  )}
                </section>
                {suggestions.length ? (
                  <section
                    className="profile-overview-card profile-completion"
                    aria-labelledby="profile-completion-title"
                  >
                    <div className="profile-section-heading">
                      <h2 className="profile-section-title" id="profile-completion-title">
                        Uzupełnij swój profil
                      </h2>
                      <span className="profile-completion-count">{3 - suggestions.length}/3</span>
                    </div>
                    <p className="profile-section-description">
                      Kilka szczegółów ułatwi współpracę w zespole. Uzupełnij je, kiedy chcesz.
                    </p>
                    <div className="profile-completion-list">
                      {suggestions.map((item) => (
                        <button
                          type="button"
                          key={item.field}
                          className="profile-completion-action"
                          disabled={pending}
                          onClick={() => edit(item.field)}
                        >
                          <span className="profile-completion-icon">
                            <Icon name={item.icon} />
                          </span>
                          <span className="profile-completion-copy">
                            <span>{item.label}</span>
                            <small>{item.description}</small>
                          </span>
                          <Icon name="chevron-right" />
                        </button>
                      ))}
                    </div>
                  </section>
                ) : null}
                <p className="profile-scope-note">
                  <Icon name="info" />
                  Dane profilu są wspólne dla Twoich Workspace.
                </p>
              </div>
              <aside
                className="tasks-issue-sidebar profile-issue-sidebar"
                aria-label="Szczegóły profilu"
              >
                <section
                  className="tasks-issue-side-section"
                  aria-labelledby="profile-contact-title"
                >
                  <div className="profile-section-heading">
                    <h2 className="profile-section-title" id="profile-contact-title">
                      <Icon name="contact" />
                      Dane kontaktowe
                    </h2>
                    <button
                      type="button"
                      className="tasks-filter-button profile-icon-action"
                      aria-label="Edytuj dane kontaktowe"
                      title="Edytuj dane kontaktowe"
                      disabled={pending}
                      onClick={() => edit('email')}
                    >
                      <Icon name="pencil" />
                    </button>
                  </div>
                  <dl className="profile-contact-list">
                    {contactDetails.map(({ label, value, icon, href, field }) => (
                      <div className="profile-contact-row" key={label}>
                        <Icon name={icon} />
                        <div className="profile-contact-value">
                          <dt>{label}</dt>
                          <dd>
                            {value ? (
                              href ? (
                                <a href={href}>{value}</a>
                              ) : (
                                <span>{value}</span>
                              )
                            ) : (
                              <button
                                type="button"
                                className="profile-text-action"
                                disabled={pending}
                                onClick={() => edit(field)}
                              >
                                Dodaj numer telefonu
                              </button>
                            )}
                          </dd>
                        </div>
                        {value ? (
                          <button
                            type="button"
                            className="tasks-filter-button profile-icon-action"
                            aria-label={`Kopiuj ${label.toLowerCase()}`}
                            title={`Kopiuj ${label.toLowerCase()}`}
                            onClick={() => void copy(value, label)}
                          >
                            <Icon name={copied === label ? 'check' : 'copy'} />
                          </button>
                        ) : null}
                      </div>
                    ))}
                  </dl>
                  <p className="profile-copy-feedback" role={copyError ? 'alert' : 'status'}>
                    {copyError || (copied ? `Skopiowano: ${copied.toLowerCase()}.` : '')}
                  </p>
                </section>
                <section
                  className="tasks-issue-side-section"
                  aria-labelledby="profile-account-title"
                >
                  <div className="profile-section-heading">
                    <h2 className="profile-section-title" id="profile-account-title">
                      <Icon name="shield-check" />
                      Konto i aktywność
                    </h2>
                  </div>
                  <div className="tasks-issue-field profile-status-side-field">
                    <span>Status</span>
                    <div className="profile-side-status-form">
                      <PresenceSelect
                        side
                        value={user.presence_status}
                        choices={presenceChoices}
                        disabled={pending}
                        onChange={(value) =>
                          void action(data.urls.update_presence_status, { presence_status: value })
                        }
                      />
                    </div>
                  </div>
                  {accountDetails.map(([label, value, className]) => (
                    <div className="tasks-issue-field" key={label}>
                      <span>{label}</span>
                      <strong className={className}>{value}</strong>
                    </div>
                  ))}
                </section>
              </aside>
            </div>
          </div>
        </main>
      </div>
      {editor === 'banner' ? (
        <BannerEditor
          data={data}
          api={initial.api_url}
          token={csrfToken}
          onClose={() => setEditor(null)}
        />
      ) : editor ? (
        <ProfileEditor
          data={data}
          api={initial.api_url}
          token={csrfToken}
          avatar={editor === 'avatar'}
          focusField={focusField}
          onClose={() => setEditor(null)}
        />
      ) : null}
    </div>
  );
}
