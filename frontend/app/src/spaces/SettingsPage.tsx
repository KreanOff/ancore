import { useCallback, useEffect, useRef, useState } from 'react';
import { EmbeddedForm, type FormDialogData } from '../forms/FormDialog';
import { Members, type MemberRow } from '../shared/Members';
import SharingDialog from '../shared/SharingDialog';
import type { Team } from '../tasks/types';
import { Icon } from '../shared/Icon';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { errorMessage } from '../shared/api';
import { type Page, pageRequest, navigate, setPageLocation } from '../shared/page';
import { ConfigurationForm, type ConfigurationSection } from './ConfigurationPage';
import type { DetailData } from './types';

type Tab = 'main' | 'members' | 'types';
type FormSection = 'main' | 'configuration';
function isConfigurationSection(value: unknown): value is 'types' {
  return value === 'types';
}
function tabFromHash(fallback: Tab): Tab {
  const key = location.hash.slice(1) || new URLSearchParams(location.search).get('section');
  if (key === 'configuration' || key === 'statuses' || key === 'fields') return 'types';
  return key === 'main' || key === 'members' || isConfigurationSection(key) ? key : fallback;
}
const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'main', label: 'Ustawienia', icon: 'settings' },
  { key: 'members', label: 'Udostępnienia', icon: 'users' },
  { key: 'types', label: 'Typy zgłoszeń', icon: 'layers' },
];

export default function SettingsPage({
  api,
  csrfToken,
  spaceUrl,
  initialTab = 'main',
  initialForm,
  initialConfiguration,
  initialDetail,
  hostId,
}: {
  api: string;
  csrfToken: string;
  spaceUrl: string;
  initialTab?: Tab | 'avatar' | 'configuration' | ConfigurationSection;
  initialForm?: FormDialogData;
  initialConfiguration?: Page;
  initialDetail?: DetailData;
  hostId?: string;
}) {
  const fallbackTab =
    initialTab === 'avatar'
      ? 'main'
      : initialTab === 'configuration' || initialTab === 'statuses' || initialTab === 'fields'
        ? 'types'
        : initialTab;
  const [data, setData] = useState(initialDetail);
  const [tab, setTab] = useState<Tab>(() => tabFromHash(fallbackTab));
  const [forms, setForms] = useState<{ main?: FormDialogData }>(() =>
    initialForm && initialTab === 'main' ? { main: initialForm } : {},
  );
  const [configuration, setConfiguration] = useState(initialConfiguration);
  const [sharing, setSharing] = useState(
    initialTab === 'members' && tab === 'members' && !!initialForm,
  );
  const [openAvatar] = useState(initialTab === 'avatar' && tab === 'main');
  const [roleMember, setRoleMember] = useState<MemberRow>();
  const [states, setStates] = useState<
    Partial<Record<FormSection, { dirty: boolean; pending: boolean }>>
  >({});
  const [acting, setActing] = useState(false);
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [life] = useState(() => new AbortController());
  const action = useRef(false);
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    setPageLocation(spaceUrl + '?view=settings#' + tab);
    window.dispatchEvent(new CustomEvent('ancore:space-settings-tab'));
  }, [spaceUrl]);
  const reportMain = useCallback((dirty: boolean, pending: boolean) => {
    setStates((s) => ({ ...s, main: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  const reportConfiguration = useCallback((dirty: boolean, pending: boolean) => {
    setStates((s) => ({ ...s, configuration: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  const request = useCallback(
    (url: string, body?: FormData) => pageRequest<Page>(api, url, csrfToken, life.signal, body),
    [api, csrfToken, life],
  );
  useEffect(() => {
    if (data) return;
    let current = true;
    request(spaceUrl + '?view=settings')
      .then((page) => {
        if (current) setData(page.data as DetailData);
      })
      .catch((exception) => {
        if (current && !life.signal.aborted) setError(errorMessage(exception));
      });
    return () => {
      current = false;
    };
  }, [data, request, spaceUrl, life]);
  useEffect(() => {
    if (
      !data ||
      tab === 'members' ||
      (tab === 'main' && !data.can_manage) ||
      (isConfigurationSection(tab) && !data.can_configure)
    )
      return;
    if (isConfigurationSection(tab) ? configuration : forms.main) return;
    let current = true;
    setError('');
    const url = tab === 'main' ? data.edit_url : data.configuration_url;
    request(url)
      .then((page) => {
        if (!current) return;
        if (isConfigurationSection(tab)) setConfiguration(page);
        else setForms({ main: page.data as FormDialogData });
      })
      .catch((exception) => {
        if (current && !life.signal.aborted) setError(errorMessage(exception));
      });
    return () => {
      current = false;
    };
  }, [tab, data, forms, configuration, request, spaceUrl, life]);
  const loading =
    !!data &&
    (isConfigurationSection(tab)
      ? data.can_configure && !configuration
      : tab === 'main'
        ? data.can_manage && !forms.main
        : false);
  const dirty = Object.values(states).some((s) => s?.dirty);
  const pending = acting || Object.values(states).some((s) => s?.pending);
  const available = tabs.filter((t) => !isConfigurationSection(t.key) || data?.can_configure);
  useDirtyGuard(dirty, pending);
  useEffect(() => {
    if (data && isConfigurationSection(tab) && !data.can_configure) setTab('main');
  }, [data, tab]);
  useEffect(() => {
    const sync = () => {
      const settingsLocation = new URL(spaceUrl + '?view=settings', location.href);
      if (
        location.pathname !== settingsLocation.pathname ||
        location.search !== settingsLocation.search
      )
        return;
      const next = pending ? tab : tabFromHash(fallbackTab);
      setTab(next);
      setPageLocation(spaceUrl + '?view=settings#' + next);
      window.dispatchEvent(new CustomEvent('ancore:space-settings-tab'));
    };
    const click = (event: MouseEvent) => {
      const link =
        event.target instanceof Element
          ? event.target.closest<HTMLAnchorElement>('[data-space-settings-tab]')
          : null;
      if (!link || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      if (pending) return;
      const next = link.dataset.spaceSettingsTab as Tab;
      if (!available.some((item) => item.key === next)) return;
      setTab(next);
      setNotice('');
      setPageLocation(spaceUrl + '?view=settings#' + next, next !== tab);
      window.dispatchEvent(new CustomEvent('ancore:space-settings-tab'));
    };
    document.addEventListener('click', click, true);
    window.addEventListener('hashchange', sync);
    window.addEventListener('popstate', sync);
    return () => {
      document.removeEventListener('click', click, true);
      window.removeEventListener('hashchange', sync);
      window.removeEventListener('popstate', sync);
    };
  }, [pending, data?.can_configure, fallbackTab, spaceUrl, tab]);
  async function refresh() {
    const page = await request(spaceUrl + '?view=settings');
    if (!life.signal.aborted) {
      const detail = page.data as DetailData;
      setData(detail);
      document.title = `${page.title} | ancore`;
      window.dispatchEvent(
        new CustomEvent('ancore:space-settings-saved', {
          detail: { name: detail.space.name },
        }),
      );
    }
  }
  async function stored(section: FormSection) {
    await refresh();
    if (section === 'configuration') {
      const page = await request(spaceUrl + 'configuration/');
      if (!life.signal.aborted) setConfiguration(page);
    }
    if (!life.signal.aborted) setNotice('Zmiany zostały zapisane.');
  }
  function close() {
    const returnUrl = initialForm?.return_url;
    void navigate(returnUrl && !returnUrl.includes('?view=settings') ? returnUrl : spaceUrl);
  }
  function membersSaved(team: Team) {
    setData((current) => (current ? { ...current, team } : current));
    setSharing(false);
    setRoleMember(undefined);
    setNotice('Dostęp został zapisany.');
  }
  async function removeMember(member: MemberRow) {
    if (action.current || pending || !data) return;
    action.current = true;
    setActing(true);
    setError('');
    try {
      const body = new FormData();
      body.set('action', 'remove');
      body.set('member_id', String(member.id));
      const team = await pageRequest<Team>(api, data.team_url, csrfToken, life.signal, body);
      if (!life.signal.aborted) membersSaved(team);
    } catch (exception) {
      if (!life.signal.aborted) setError(errorMessage(exception));
    } finally {
      action.current = false;
      if (!life.signal.aborted) setActing(false);
    }
  }
  return (
    <>
      <div className="tasks-page work-page space-settings-page" data-react-screen="space-settings">
        <header className="tasks-topbar tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <a
              href={spaceUrl}
              className="tasks-issue-close"
              aria-label="Wróć do przestrzeni"
              title="Wróć do przestrzeni"
            >
              <Icon name="arrow-left" />
            </a>
            <h1 className="tasks-topbar-title">
              Ustawienia przestrzeni{data ? ` · ${data.space.name}` : ''}
            </h1>
          </div>
        </header>
        {error ? (
          <div className="tasks-modal__errors space-settings-message" role="alert">
            {error}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                setError('');
                if (data) setData({ ...data });
                else void refresh().catch((e) => setError(errorMessage(e)));
              }}
            >
              Spróbuj ponownie
            </button>
          </div>
        ) : null}
        {notice ? (
          <p className="space-settings-message" role="status">
            {notice}
          </p>
        ) : null}
        {(!data || loading) && !error ? (
          <p className="space-settings-message" role="status">
            Wczytywanie ustawień…
          </p>
        ) : null}
        {available
          .filter((t) => !isConfigurationSection(t.key))
          .map((t) => (
            <section
              key={t.key}
              id={`space-settings-panel-${t.key}`}
              aria-label={t.label}
              hidden={tab !== t.key}
              className="space-settings-panel"
            >
              {t.key === 'main' && forms.main ? (
                <EmbeddedForm
                  data={forms.main}
                  api={api}
                  csrfToken={csrfToken}
                  onSaved={() => stored('main')}
                  onStateChange={reportMain}
                  onCancel={close}
                  openAvatar={openAvatar}
                />
              ) : null}
              {t.key === 'main' && data && !data.can_manage ? (
                <>
                  <div className="tasks-modal__body">
                    <h3>{data.space.name}</h3>
                    <p>{data.space.description}</p>
                    <p>
                      {data.space.kind_label} · {data.space.template_label}
                    </p>
                    <p>{data.space.management_label}</p>
                    <p>
                      Widoczność:{' '}
                      {data.space.visibility === 'private'
                        ? 'prywatna — wybrane osoby'
                        : 'cały Workspace'}
                    </p>
                  </div>
                  <footer className="tasks-modal__footer">
                    <button type="button" className="btn btn-secondary" onClick={close}>
                      Zamknij
                    </button>
                  </footer>
                </>
              ) : null}
              {t.key === 'members' && data ? (
                <>
                  <div className="tasks-modal__body">
                    <div className="workplace-edit-modal__team-toolbar">
                      <span className="workplaces-management__count">
                        {data.space.name} · Członkowie: {data.team.members.length}
                      </span>
                      {data.team.can_manage ? (
                        <button
                          type="button"
                          className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
                          disabled={pending}
                          onClick={() => setSharing(true)}
                          aria-haspopup="dialog"
                        >
                          <Icon name="plus" />
                          Udostępnij
                        </button>
                      ) : null}
                    </div>
                    {data.space.visibility === 'public' ? (
                      <p className="workplace-team__hint">
                        Dostęp mają aktywni członkowie Workspace. Aby udostępniać wybranym osobom,
                        zapisz widoczność „Prywatna” w zakładce „Ustawienia”.
                      </p>
                    ) : null}
                    <Members
                      members={data.team.members}
                      isOwner={data.team.is_owner}
                      canEditRoles={data.team.can_manage}
                      busy={pending}
                      onRole={setRoleMember}
                      onRemove={(member) =>
                        window.showConfirmModal({
                          title: 'Odbierz dostęp',
                          messageText: `Odebrać dostęp do przestrzeni osobie ${member.name}? Utraci też dostęp do jej zadań.`,
                          confirmText: 'Odbierz dostęp',
                          cancelText: 'Anuluj',
                          onConfirm: () => void removeMember(member),
                        })
                      }
                    />
                  </div>
                  <footer className="tasks-modal__footer">
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={pending}
                      onClick={close}
                    >
                      Zamknij
                    </button>
                  </footer>
                </>
              ) : null}
            </section>
          ))}
        {data?.can_configure && configuration ? (
          <section className="space-settings-panel" hidden={!isConfigurationSection(tab)}>
            <ConfigurationForm
              key={(configuration.data as { revision: string }).revision}
              initial={configuration}
              csrfToken={csrfToken}
              onSaved={() => stored('configuration')}
              onStateChange={reportConfiguration}
              onCancel={close}
              hostId={hostId}
            />
          </section>
        ) : null}
      </div>
      {data && (sharing || roleMember) ? (
        <SharingDialog<Team>
          name={data.space.name}
          schema={data.team.share_form}
          person={roleMember}
          api={api}
          url={data.team_url}
          csrfToken={csrfToken}
          hostId={hostId}
          onClose={() => {
            setSharing(false);
            setRoleMember(undefined);
          }}
          onSaved={membersSaved}
        />
      ) : null}
    </>
  );
}
