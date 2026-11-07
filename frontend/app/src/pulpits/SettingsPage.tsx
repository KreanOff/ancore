import { PageHeader } from '../shared/PageHeader';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { EmbeddedForm } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import AccessEditor from './AccessEditor';
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
  const reportAccess = useCallback((dirty: boolean, pending: boolean) => {
    setStates((previous) => ({ ...previous, access: { dirty, pending } }));
  }, []);
  function accessSaved(result: EditData['team']) {
    setTeam(result);
    if (
      (team.visibility === 'workspace') !== (result.visibility === 'workspace') &&
      !states.settings?.dirty
    ) {
      setPages((previous) => ({ ...previous, settings: undefined }));
    }
  }
  function close() {
    void navigate(initialData.return_url);
  }
  return (
    <>
      <div
        className="tasks-page work-page space-settings-page pulpit-settings-page"
        data-react-screen="pulpit-settings"
      >
        <PageHeader
          heading={
            <>
              <a
                href={initialData.return_url}
                className="tasks-issue-close"
                aria-label={returnLabel}
                title={returnLabel}
              >
                <Icon name="arrow-left" />
              </a>
              <h1 className="tasks-topbar-title">Ustawienia pulpitu · {team.name}</h1>
            </>
          }
        />
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
                <AccessEditor
                  team={team}
                  api={initial.api_url}
                  url={initialData.team_url}
                  csrfToken={csrfToken}
                  settingsDirty={!!states.settings?.dirty}
                  blocked={acting || !!states.settings?.pending}
                  onSaved={accessSaved}
                  onStateChange={reportAccess}
                />
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
    </>
  );
}
