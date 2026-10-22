import { useCallback, useEffect, useRef, useState } from 'react';
import { EmbeddedForm, FormDialog, type FormDialogData } from '../forms/FormDialog';
import { Avatar } from '../shared/Avatar';
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
  const [memberForm, setMemberForm] = useState(initialTab === 'members' ? initialForm : undefined);
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
  async function memberAction(url: string, remove = false) {
    if (action.current || pending) return;
    action.current = true;
    setActing(true);
    setError('');
    try {
      if (remove) {
        await request(url, new FormData());
        saved.current = true;
        await refresh();
      } else {
        const page = await request(url);
        if (!life.signal.aborted) setMemberForm(page.data as FormDialogData);
      }
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
                  <div className="work-panel-heading">
                    <h3>Członkowie i role</h3>
                    {data.can_manage && data.space.visibility === 'private' ? (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        disabled={pending}
                        onClick={() => void memberAction(data.member_url)}
                      >
                        <Icon name="user-round-plus" />
                        Udostępnij / zmień rolę
                      </button>
                    ) : null}
                  </div>
                  {data.space.visibility === 'public' ? (
                    <p>Dostęp mają aktywni członkowie Workspace.</p>
                  ) : (
                    <>
                      <p>{data.private_owner} · Właściciel</p>
                      {data.members.length ? (
                        data.members.map((member) => (
                          <div className="work-member" key={member.id}>
                            <Avatar data={member.avatar} className="tasks-directory-avatar" />
                            <span>{member.name}</span>
                            <span>{member.role}</span>
                            {member.can_remove ? (
                              <button
                                type="button"
                                className="btn btn-secondary"
                                disabled={pending}
                                onClick={() =>
                                  window.showConfirmModal({
                                    title: 'Odbierz dostęp',
                                    message: `Odebrać dostęp do przestrzeni osobie ${member.name}?`,
                                    confirmText: 'Odbierz dostęp',
                                    cancelText: 'Anuluj',
                                    onConfirm: () => void memberAction(member.remove_url, true),
                                  })
                                }
                              >
                                Odbierz dostęp
                              </button>
                            ) : null}
                          </div>
                        ))
                      ) : (
                        <p>Nie udostępniono jeszcze przestrzeni innym osobom.</p>
                      )}
                    </>
                  )}
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
      {memberForm ? (
        <FormDialog
          data={{ ...memberForm, space_settings: undefined }}
          api={api}
          csrfToken={csrfToken}
          hostId={hostId}
          onClose={() => setMemberForm(undefined)}
          onSaved={async () => {
            saved.current = true;
            await refresh();
            setMemberForm(undefined);
            setNotice('Dostęp został zapisany.');
          }}
        />
      ) : null}
    </>
  );
}
