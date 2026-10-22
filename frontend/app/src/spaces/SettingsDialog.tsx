import { useCallback, useEffect, useRef, useState } from 'react';
import { EmbeddedForm, type FormDialogData } from '../forms/FormDialog';
import { Members, type MemberRow } from '../shared/Members';
import SharingDialog from '../shared/SharingDialog';
import type { Team } from '../tasks/types';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { errorMessage } from '../shared/api';
import { type Page, pageRequest } from '../shared/page';
import { ConfigurationForm } from './ConfigurationPage';
import type { DetailData } from './types';

type Tab = 'main' | 'members' | 'configuration';
const tabs: { key: Tab; label: string; icon: string }[] = [
  { key: 'main', label: 'Główna', icon: 'settings' },
  { key: 'members', label: 'Członkowie', icon: 'users' },
  { key: 'configuration', label: 'Statusy, typy i pola', icon: 'list-checks' },
];

export default function SettingsDialog({
  api,
  csrfToken,
  spaceUrl,
  initialTab = 'main',
  initialForm,
  initialConfiguration,
  initialDetail,
  onClose,
  onSaved,
  hostId,
}: {
  api: string;
  csrfToken: string;
  spaceUrl: string;
  initialTab?: Tab | 'avatar';
  initialForm?: FormDialogData;
  initialConfiguration?: Page;
  initialDetail?: DetailData;
  onClose: () => void;
  onSaved: (url: string) => void;
  hostId?: string;
}) {
  const [data, setData] = useState(initialDetail);
  const [tab, setTab] = useState<Tab>(initialTab === 'avatar' ? 'main' : initialTab);
  const [forms, setForms] = useState<Partial<Record<Tab, FormDialogData>>>(() =>
    initialForm && initialTab !== 'members' && initialTab !== 'avatar'
      ? { [initialTab]: initialForm }
      : {},
  );
  const [configuration, setConfiguration] = useState(initialConfiguration);
  const [sharing, setSharing] = useState(initialTab === 'members' && !!initialForm);
  const [roleMember, setRoleMember] = useState<MemberRow>();
  const [states, setStates] = useState<Partial<Record<Tab, { dirty: boolean; pending: boolean }>>>(
    {},
  );
  const [acting, setActing] = useState(false);
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [life] = useState(() => new AbortController());
  const saved = useRef(false),
    action = useRef(false);
  useEffect(() => () => life.abort(), [life]);
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
      (tab === 'configuration' && !data.can_configure)
    )
      return;
    if (tab === 'configuration' ? configuration : forms[tab]) return;
    let current = true;
    setError('');
    const url = tab === 'main' ? data.edit_url : data.configuration_url;
    request(url)
      .then((page) => {
        if (!current) return;
        if (tab === 'configuration') setConfiguration(page);
        else setForms((s) => ({ ...s, [tab]: page.data as FormDialogData }));
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
    (tab === 'configuration'
      ? data.can_configure && !configuration
      : tab === 'main'
        ? data.can_manage && !forms[tab]
        : false);
  const dirty = Object.values(states).some((s) => s?.dirty);
  const pending = acting || Object.values(states).some((s) => s?.pending);
  const available = tabs.filter((t) => t.key !== 'configuration' || data?.can_configure);
  async function refresh() {
    const page = await request(spaceUrl + '?view=settings');
    if (!life.signal.aborted) setData(page.data as DetailData);
  }
  async function stored(section: Tab) {
    saved.current = true;
    await refresh();
    if (section === 'configuration') {
      const page = await request(spaceUrl + 'configuration/');
      if (!life.signal.aborted) setConfiguration(page);
    }
    if (!life.signal.aborted) setNotice('Zmiany zostały zapisane.');
  }
  function close() {
    if (saved.current) onSaved(initialForm?.return_url.replace('?view=settings', '') || spaceUrl);
    else onClose();
  }
  function requestClose(element: HTMLElement) {
    const modal = element.closest<HTMLElement>('.tasks-modal');
    if (modal) window.AncoreTaskModals?.close(modal);
  }
  function membersSaved(team: Team) {
    saved.current = true;
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
      <Modal
        title="Ustawienia przestrzeni"
        className="work-modal space-settings-modal"
        dirty={dirty}
        pending={pending}
        onClose={close}
        hostId={hostId}
      >
        <div
          className="notifications-tabs space-settings-tabs"
          role="tablist"
          aria-label="Ustawienia przestrzeni"
          onKeyDown={(event) => {
            const index = available.findIndex((t) => t.key === tab);
            const next =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? available.length - 1
                  : event.key === 'ArrowRight'
                    ? (index + 1) % available.length
                    : event.key === 'ArrowLeft'
                      ? (index + available.length - 1) % available.length
                      : -1;
            if (next < 0 || pending) return;
            event.preventDefault();
            setTab(available[next].key);
            event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
          }}
        >
          {available.map((t) => (
            <button
              type="button"
              key={t.key}
              id={`space-settings-tab-${t.key}`}
              role="tab"
              aria-selected={tab === t.key}
              aria-controls={`space-settings-panel-${t.key}`}
              tabIndex={tab === t.key ? 0 : -1}
              disabled={pending}
              onClick={() => {
                setTab(t.key);
                setNotice('');
              }}
            >
              <Icon name={t.icon} />
              {t.label}
            </button>
          ))}
        </div>
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
        {available.map((t) => (
          <section
            key={t.key}
            id={`space-settings-panel-${t.key}`}
            role="tabpanel"
            aria-labelledby={`space-settings-tab-${t.key}`}
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
                openAvatar={initialTab === 'avatar'}
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
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={(e) => requestClose(e.currentTarget)}
                  >
                    Zamknij
                  </button>
                </footer>
              </>
            ) : null}
            {t.key === 'configuration' && configuration ? (
              <ConfigurationForm
                key={(configuration.data as { revision: string }).revision}
                initial={configuration}
                csrfToken={csrfToken}
                onSaved={() => stored('configuration')}
                onStateChange={reportConfiguration}
              />
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
                      zapisz widoczność „Prywatna” w zakładce „Główna”.
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
                        message: `Odebrać dostęp do przestrzeni osobie ${member.name}? Utraci też dostęp do jej zadań.`,
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
                    onClick={(e) => requestClose(e.currentTarget)}
                  >
                    Zamknij
                  </button>
                </footer>
              </>
            ) : null}
          </section>
        ))}
      </Modal>
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
