import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { EmbeddedForm } from '../forms/FormDialog';
import { Members, type MemberRow } from '../shared/Members';
import SharingDialog from '../shared/SharingDialog';
import { Icon } from '../shared/Icon';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest, setPageLocation } from '../shared/page';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import type { EditData } from './types';

type Tab = EditData['section'];
function tabFromHash(fallback: Tab): Tab {
  const key = location.hash.slice(1);
  return key === 'settings' || key === 'access' ? key : fallback;
}

export default function SettingsPage({ initial, csrfToken }: PageProps) {
  const initialData = initial.data as EditData;
  const [tab, setTab] = useState<Tab>(() => tabFromHash(initialData.section));
  const [team, setTeam] = useState(initialData.team);
  const [sharing, setSharing] = useState(false);
  const [roleMember, setRoleMember] = useState<MemberRow>();
  const [acting, setActing] = useState(false);
  const action = useRef(false);
  const retryAction = useRef<(() => void) | undefined>();
  const [pages, setPages] = useState<Partial<Record<Tab, Page>>>(() => ({
    [initialData.section]: initial,
  }));
  const [states, setStates] = useState<Partial<Record<Tab, { dirty: boolean; pending: boolean }>>>(
    {},
  );
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [life] = useState(() => new AbortController());
  const tabs = useMemo(
    () =>
      initialData.settings_tabs.filter(
        (item): item is typeof item & { key: Tab } => item.key !== 'gadgets',
      ),
    [initialData.settings_tabs],
  );
  const dirty = Object.values(states).some((state) => state?.dirty);
  const pending = acting || Object.values(states).some((state) => state?.pending);
  const settingsUrl = tabs.find((item) => item.key === 'settings')!.url;
  const returnLabel =
    initialData.return_url === initialData.dashboard.url ? 'Wróć do pulpitu' : 'Wróć do pulpitów';
  useDirtyGuard(dirty, pending);
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    setPageLocation(settingsUrl + '#' + tab);
    window.dispatchEvent(new CustomEvent('ancore:pulpit-settings-tab'));
  }, [settingsUrl]);
  useEffect(() => {
    const select = (next: Tab, push = false) => {
      setTab(next);
      if (next !== tab) {
        setNotice('');
        setError('');
        retryAction.current = undefined;
      }
      setPageLocation(settingsUrl + '#' + next, push);
      window.dispatchEvent(new CustomEvent('ancore:pulpit-settings-tab'));
    };
    const sync = () => {
      const target = new URL(settingsUrl, location.href);
      if (location.pathname !== target.pathname || location.search !== target.search) return;
      select(pending ? tab : tabFromHash(initialData.section));
    };
    const click = (event: MouseEvent) => {
      const link =
        event.target instanceof Element
          ? event.target.closest<HTMLAnchorElement>('[data-pulpit-settings-tab]')
          : null;
      if (!link || event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey)
        return;
      event.preventDefault();
      if (pending) return;
      const next = link.dataset.pulpitSettingsTab as Tab;
      if (tabs.some((item) => item.key === next)) select(next, next !== tab);
    };
    document.addEventListener('click', click, true);
    window.addEventListener('hashchange', sync);
    window.addEventListener('popstate', sync);
    return () => {
      document.removeEventListener('click', click, true);
      window.removeEventListener('hashchange', sync);
      window.removeEventListener('popstate', sync);
    };
  }, [pending, tab, tabs, settingsUrl, initialData.section]);
  useEffect(() => {
    if (tab === 'access' || pages[tab]) return;
    let current = true;
    setError('');
    retryAction.current = undefined;
    pageRequest<Page>(
      initial.api_url,
      tabs.find((item) => item.key === tab)!.url,
      csrfToken,
      life.signal,
    )
      .then((page) => {
        if (current) {
          setPages((previous) => ({ ...previous, [tab]: page }));
          setTeam((page.data as EditData).team);
        }
      })
      .catch((exception) => {
        if (current && !life.signal.aborted) setError(errorMessage(exception));
      });
    return () => {
      current = false;
    };
  }, [tab, pages, tabs, initial.api_url, csrfToken, life, attempt]);
  const reportSettings = useCallback((dirty: boolean, pending: boolean) => {
    setStates((previous) => ({ ...previous, settings: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  async function saved() {
    if (action.current) return;
    action.current = true;
    setActing(true);
    setError('');
    retryAction.current = undefined;
    try {
      const result = await pageRequest<EditData['team']>(
        initial.api_url,
        initialData.team_url,
        csrfToken,
        life.signal,
      );
      if (life.signal.aborted) return;
      setTeam(result);
      document.title = `Ustawienia pulpitu · ${result.name} | ancore`;
      window.dispatchEvent(
        new CustomEvent('ancore:pulpit-settings-saved', {
          detail: { name: result.name },
        }),
      );
      setNotice('Zmiany zostały zapisane.');
    } catch (exception) {
      if (!life.signal.aborted) {
        setError(
          `Zmiany zapisano, ale nie udało się odświeżyć ustawień. ${errorMessage(exception)}`,
        );
        retryAction.current = () => void saved();
      }
    } finally {
      action.current = false;
      if (!life.signal.aborted) setActing(false);
    }
  }
  function shared(result: EditData['team']) {
    setTeam(result);
    setSharing(false);
    setRoleMember(undefined);
    setNotice('Dostęp został zapisany.');
  }
  function close() {
    void navigate(initialData.return_url);
  }
  async function removeMember(member: MemberRow) {
    if (action.current || pending) return;
    action.current = true;
    setActing(true);
    setError('');
    retryAction.current = undefined;
    try {
      const body = new FormData();
      body.set('action', 'remove');
      body.set('member_id', String(member.id));
      const result = await pageRequest<EditData['team']>(
        initial.api_url,
        initialData.team_url,
        csrfToken,
        life.signal,
        body,
      );
      if (!life.signal.aborted) shared(result);
    } catch (exception) {
      if (!life.signal.aborted) {
        setError(errorMessage(exception));
        retryAction.current = () => void removeMember(member);
      }
    } finally {
      action.current = false;
      if (!life.signal.aborted) setActing(false);
    }
  }
  return (
    <>
      <div
        className="tasks-page work-page space-settings-page pulpit-settings-page"
        data-react-screen="pulpit-settings"
      >
        <header className="tasks-topbar tasks-topbar--project-directory">
          <div className="tasks-titlebar-left">
            <a
              href={initialData.return_url}
              className="tasks-issue-close"
              aria-label={returnLabel}
              title={returnLabel}
            >
              <Icon name="arrow-left" />
            </a>
            <h1 className="tasks-topbar-title">Ustawienia pulpitu · {team.name}</h1>
          </div>
        </header>
        {error ? (
          <div className="tasks-modal__errors space-settings-message" role="alert">
            {error}
            <button
              type="button"
              className="btn btn-secondary"
              disabled={pending}
              onClick={() =>
                retryAction.current ? retryAction.current() : setAttempt((value) => value + 1)
              }
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
        {tab !== 'access' && !pages[tab] && !error ? (
          <p className="space-settings-message" role="status">
            Wczytywanie ustawień…
          </p>
        ) : null}
        {tabs.map((item) => {
          const page = pages[item.key];
          const data = page?.data as EditData | undefined;
          return (
            <section
              key={item.key}
              id={`pulpit-settings-panel-${item.key}`}
              aria-label={item.label}
              hidden={tab !== item.key}
              className="space-settings-panel pulpit-settings-panel"
            >
              {item.key === 'access' ? (
                <>
                  <div className="tasks-modal__body">
                    <div className="workplace-edit-modal__team-toolbar">
                      <span className="workplaces-management__count">
                        {team.name} · Osoby: {team.members.length}
                      </span>
                      {team.can_manage ? (
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
                    {team.visibility === 'workspace' ? (
                      <p className="workplace-team__hint">
                        Dostęp mają aktywni członkowie Workspace. Aby udostępniać wybranym osobom,
                        zapisz widoczność „Prywatny — wybrane osoby” w zakładce „Ustawienia”.
                      </p>
                    ) : null}
                    <Members
                      members={team.members}
                      isOwner={team.is_owner}
                      canEditRoles={team.can_manage}
                      busy={pending}
                      onRole={setRoleMember}
                      onRemove={(member) =>
                        window.showConfirmModal({
                          title: 'Odbierz dostęp',
                          messageText: `Odebrać dostęp do pulpitu osobie ${member.name}?`,
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
              ) : page && data ? (
                <EmbeddedForm
                  data={{
                    title: item.label,
                    action: data.action,
                    return_url: data.return_url,
                    form: data.form,
                  }}
                  api={initial.api_url}
                  csrfToken={csrfToken}
                  onSaved={saved}
                  onStateChange={reportSettings}
                  onCancel={close}
                />
              ) : null}
            </section>
          );
        })}
      </div>
      {sharing || roleMember ? (
        <SharingDialog<EditData['team']>
          name={team.name}
          schema={team.share_form}
          person={roleMember}
          api={initial.api_url}
          url={initialData.team_url}
          csrfToken={csrfToken}
          onClose={() => {
            setSharing(false);
            setRoleMember(undefined);
          }}
          onSaved={shared}
        />
      ) : null}
    </>
  );
}
