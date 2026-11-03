import { useCallback, useEffect, useState } from 'react';
import { EmbeddedForm, type FormDialogData } from '../forms/FormDialog';
import AccessEditor, { type AccessTeam } from '../shared/AccessEditor';
import { Icon } from '../shared/Icon';
import { SpaceHeader } from './SpaceHeader';
import { useDirtyGuard } from '../shared/useDirtyGuard';
import { errorMessage } from '../shared/api';
import { type Page, pageRequest, navigate, setPageLocation } from '../shared/page';
import {
  ConfigurationForm,
  type ConfigurationData,
  type ConfigurationSection,
  type EditableConfigurationSection,
} from './ConfigurationPage';
import type { DetailData } from './types';

type Tab = 'main' | 'members' | EditableConfigurationSection;
type FormSection = 'main' | 'configuration' | 'members';
function isConfigurationSection(value: unknown): value is EditableConfigurationSection {
  return value === 'types' || value === 'statuses' || value === 'categories' || value === 'groups';
}
function tabFromHash(fallback: Tab): Tab {
  const key = location.hash.slice(1) || new URLSearchParams(location.search).get('section');
  if (key === 'configuration' || key === 'fields') return 'types';
  return key === 'main' || key === 'members' || isConfigurationSection(key) ? key : fallback;
}
const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'main', label: 'Ustawienia', icon: 'settings' },
  { key: 'members', label: 'Udostępnienia', icon: 'users' },
  { key: 'types', label: 'Typy zgłoszeń', icon: 'layers' },
  { key: 'categories', label: 'Kategorie', icon: 'list' },
  { key: 'groups', label: 'Grupy', icon: 'folder' },
  { key: 'statuses', label: 'Proces pracy', icon: 'workflow' },
];
const workflowViews = [
  { key: 'states', label: 'Stany', icon: 'list-checks' },
  { key: 'map', label: 'Mapa', icon: 'workflow' },
] as const;

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
      : initialTab === 'configuration' || initialTab === 'fields'
        ? 'types'
        : initialTab;
  const [data, setData] = useState(initialDetail);
  const [tab, setTab] = useState<Tab>(() => tabFromHash(fallbackTab));
  const [forms, setForms] = useState<{ main?: FormDialogData }>(() =>
    initialForm && initialTab === 'main' ? { main: initialForm } : {},
  );
  const [configuration, setConfiguration] = useState(initialConfiguration);
  const [workflowView, setWorkflowView] = useState<'states' | 'map'>(() =>
    (initialConfiguration?.data as ConfigurationData | undefined)?.workflow_view === 'map'
      ? 'map'
      : 'states',
  );
  const [openAvatar] = useState(initialTab === 'avatar' && tab === 'main');
  const [states, setStates] = useState<
    Partial<Record<FormSection, { dirty: boolean; pending: boolean }>>
  >({});
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [life] = useState(() => new AbortController());
  useEffect(() => () => life.abort(), [life]);
  useEffect(() => {
    setPageLocation(spaceUrl + '?view=settings#' + tab);
    window.dispatchEvent(new CustomEvent('ancore:space-settings-tab'));
  }, [spaceUrl]);
  const reportMain = useCallback((dirty: boolean, pending: boolean) => {
    setStates((s) => ({ ...s, main: { dirty, pending } }));
    if (dirty || pending) setNotice('');
  }, []);
  const reportMembers = useCallback((dirty: boolean, pending: boolean) => {
    setStates((s) => ({ ...s, members: { dirty, pending } }));
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
  const pending = Object.values(states).some((s) => s?.pending);
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
  function clearUnavailableSections(canManage: boolean, canConfigure?: boolean) {
    if (!canManage) setForms({});
    if (canConfigure === false) setConfiguration(undefined);
    if (!canManage || canConfigure === false) {
      setStates((current) => {
        const next = { ...current };
        if (!canManage) delete next.main;
        if (canConfigure === false) delete next.configuration;
        return next;
      });
    }
  }
  async function refresh() {
    const page = await request(spaceUrl + '?view=settings');
    if (!life.signal.aborted) {
      const detail = page.data as DetailData;
      setData(detail);
      clearUnavailableSections(detail.can_manage, detail.can_configure);
      document.title = `${page.title} | ancore`;
      window.dispatchEvent(
        new CustomEvent('ancore:space-settings-saved', {
          detail: { name: detail.space.name, canConfigure: detail.can_configure },
        }),
      );
      return detail;
    }
  }
  async function stored(section: FormSection) {
    // EmbeddedForm finishes its POST before this read. Keep navigation blocked
    // until the refreshed permissions and any configuration snapshot arrive.
    setStates((current) => ({
      ...current,
      [section]: { dirty: current[section]?.dirty ?? false, pending: true },
    }));
    try {
      const detail = await refresh();
      if (section === 'configuration' && detail?.can_configure) {
        const page = await request(spaceUrl + 'configuration/');
        if (!life.signal.aborted) setConfiguration(page);
      }
      if (!life.signal.aborted) setNotice('Zmiany zostały zapisane.');
    } finally {
      if (!life.signal.aborted) {
        setStates((current) =>
          current[section]
            ? { ...current, [section]: { ...current[section], pending: false } }
            : current,
        );
      }
    }
  }
  function close() {
    const returnUrl = initialForm?.return_url;
    void navigate(returnUrl && !returnUrl.includes('?view=settings') ? returnUrl : spaceUrl);
  }
  function membersSaved(team: AccessTeam) {
    if (data?.team.visibility !== team.visibility && !states.main?.dirty) {
      setForms({});
    }
    clearUnavailableSections(team.can_manage, team.can_configure);
    setData((current) =>
      current
        ? {
            ...current,
            space: { ...current.space, visibility: team.visibility },
            team,
            can_manage: team.can_manage,
            can_configure: team.can_configure ?? current.can_configure,
          }
        : current,
    );
    window.dispatchEvent(
      new CustomEvent('ancore:space-settings-saved', {
        detail: { name: team.name, canConfigure: team.can_configure },
      }),
    );
  }
  return (
    <>
      <div className="tasks-page work-page space-settings-page" data-react-screen="space-settings">
        <SpaceHeader
          heading={
            <>
              <a
                href={spaceUrl}
                className="tasks-issue-close"
                aria-label="Wróć do przestrzeni"
                title="Wróć do przestrzeni"
              >
                <Icon name="arrow-left" />
              </a>
              <h1 className="tasks-topbar-title work-space-title">
                Ustawienia przestrzeni{data ? ` · ${data.space.name}` : ''}
              </h1>
            </>
          }
          actions={null}
          navigationContent={
            tab === 'statuses' && data?.can_configure && configuration ? (
              <nav
                className="notifications-tabs work-tabs work-tabs--views"
                role="tablist"
                aria-label="Widoki procesu pracy"
              >
                {workflowViews.map((view, index) => (
                  <button
                    key={view.key}
                    type="button"
                    role="tab"
                    id={`workflow-tab-${view.key}`}
                    aria-selected={workflowView === view.key}
                    aria-controls="workflow-view-panel"
                    tabIndex={workflowView === view.key ? 0 : -1}
                    disabled={pending}
                    onClick={() => setWorkflowView(view.key)}
                    onKeyDown={(event) => {
                      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
                      event.preventDefault();
                      const next = event.key === 'Home' ? 0 : event.key === 'End' ? 1 : 1 - index;
                      setWorkflowView(workflowViews[next].key);
                      document.getElementById(`workflow-tab-${workflowViews[next].key}`)?.focus();
                    }}
                  >
                    <Icon name={view.icon} />
                    {view.label}
                  </button>
                ))}
              </nav>
            ) : null
          }
        />
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
              onSubmitCapture={(event) => {
                if (
                  t.key !== 'main' ||
                  !states.configuration?.dirty ||
                  !data ||
                  !(event.target instanceof HTMLFormElement)
                )
                  return;
                const visibility = new FormData(event.target).get('visibility');
                if (visibility === null || visibility === data.space.visibility) return;
                event.preventDefault();
                event.stopPropagation();
                setNotice(
                  'Najpierw zapisz lub anuluj zmiany konfiguracji zadań, aby zmienić widoczność przestrzeni.',
                );
              }}
            >
              {t.key === 'main' && data?.can_manage && forms.main ? (
                <EmbeddedForm
                  data={forms.main}
                  api={api}
                  csrfToken={csrfToken}
                  onSaved={() => stored('main')}
                  onStateChange={reportMain}
                  onCancel={close}
                  actionsPosition="toolbar"
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
                <AccessEditor
                  saveOnAction
                  directory
                  team={data.team}
                  publicVisibility="public"
                  api={api}
                  url={data.team_url}
                  csrfToken={csrfToken}
                  hostId={hostId}
                  initialSharing={initialTab === 'members' && tab === 'members' && !!initialForm}
                  settingsDirty={!!states.main?.dirty || !!states.configuration?.dirty}
                  blocked={!!states.main?.pending || !!states.configuration?.pending}
                  onSaved={membersSaved}
                  onStateChange={reportMembers}
                />
              ) : null}
            </section>
          ))}
        {data?.can_configure && configuration ? (
          <section className="space-settings-panel" hidden={!isConfigurationSection(tab)}>
            <ConfigurationForm
              key={(configuration.data as { revision: string }).revision}
              initial={configuration}
              section={isConfigurationSection(tab) ? tab : 'types'}
              workflowView={workflowView}
              commitOnSubmit={isConfigurationSection(tab) && tab !== 'statuses'}
              csrfToken={csrfToken}
              onSaved={() => stored('configuration')}
              onStateChange={reportConfiguration}
              onCancel={close}
              hostId={hostId}
            />
          </section>
        ) : null}
      </div>
    </>
  );
}
