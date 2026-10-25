import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { EmbeddedForm } from '../forms/FormDialog';
import { Members, type MemberRow } from '../shared/Members';
import SharingDialog from '../shared/SharingDialog';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { errorMessage } from '../shared/api';
import { type Page, type PageProps, navigate, pageRequest } from '../shared/page';
import { DashboardView } from './DetailPage';
import type { EditData, SettingsTab } from './types';

export default function SettingsDialog({
  initial,
  csrfToken,
  onClose,
  hostId,
}: PageProps & { onClose: (changed: boolean) => void; hostId?: string }) {
  const initialData = initial.data as EditData;
  const [tab, setTab] = useState<SettingsTab>(initialData.section);
  const [team, setTeam] = useState(initialData.team);
  const [sharing, setSharing] = useState(false);
  const [roleMember, setRoleMember] = useState<MemberRow>();
  const [acting, setActing] = useState(false);
  const action = useRef(false);
  const retryAction = useRef<(() => void) | undefined>();
  const [pages, setPages] = useState<Partial<Record<SettingsTab, Page>>>(() => ({
    [tab]: initial,
  }));
  const [states, setStates] = useState<
    Partial<Record<SettingsTab, { dirty: boolean; pending: boolean }>>
  >({});
  const [error, setError] = useState(''),
    [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [life] = useState(() => new AbortController());
  const changed = useRef(false);
  const tabs = useMemo(
    () => initialData.settings_tabs.filter((item) => item.key !== 'gadgets'),
    [initialData.settings_tabs],
  );
  const dirty = Object.values(states).some((state) => state?.dirty);
  const pending = acting || Object.values(states).some((state) => state?.pending);
  useEffect(() => () => life.abort(), [life]);
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
    changed.current = true;
    const result = await pageRequest<EditData['team']>(
      initial.api_url,
      initialData.team_url,
      csrfToken,
      life.signal,
    );
    if (life.signal.aborted) return;
    setTeam(result);
    setNotice('Zmiany zostały zapisane.');
  }
  function shared(result: EditData['team']) {
    changed.current = true;
    setTeam(result);
    setSharing(false);
    setRoleMember(undefined);
    setNotice('Dostęp został zapisany.');
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
      <Modal
        title="Ustawienia pulpitu"
        className="work-modal pulpit-settings-modal"
        dirty={dirty}
        pending={pending}
        onClose={() => onClose(changed.current)}
        hostId={hostId}
      >
        <div
          className="notifications-tabs pulpit-settings-tabs"
          role="tablist"
          aria-label="Ustawienia pulpitu"
          onKeyDown={(event) => {
            const index = tabs.findIndex((item) => item.key === tab);
            const next =
              event.key === 'Home'
                ? 0
                : event.key === 'End'
                  ? tabs.length - 1
                  : event.key === 'ArrowRight'
                    ? (index + 1) % tabs.length
                    : event.key === 'ArrowLeft'
                      ? (index + tabs.length - 1) % tabs.length
                      : -1;
            if (next < 0 || pending) return;
            event.preventDefault();
            setTab(tabs[next].key);
            retryAction.current = undefined;
            setError('');
            setNotice('');
            event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
          }}
        >
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              id={`pulpit-settings-tab-${item.key}`}
              role="tab"
              aria-selected={tab === item.key}
              aria-controls={`pulpit-settings-panel-${item.key}`}
              tabIndex={tab === item.key ? 0 : -1}
              disabled={pending}
              onClick={() => {
                setTab(item.key);
                retryAction.current = undefined;
                setError('');
                setNotice('');
              }}
            >
              <Icon name={item.icon} />
              {item.label}
            </button>
          ))}
        </div>
        {error ? (
          <div className="tasks-modal__errors pulpit-settings-message" role="alert">
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
          <p className="pulpit-settings-message" role="status">
            {notice}
          </p>
        ) : null}
        {tab !== 'access' && !pages[tab] && !error ? (
          <p className="pulpit-settings-message" role="status">
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
              role="tabpanel"
              aria-labelledby={`pulpit-settings-tab-${item.key}`}
              hidden={tab !== item.key}
              className="pulpit-settings-panel"
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
                      onClick={(event) => {
                        const modal = event.currentTarget.closest<HTMLElement>('.tasks-modal');
                        if (modal) window.AncoreTaskModals?.close(modal);
                      }}
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
                />
              ) : null}
            </section>
          );
        })}
      </Modal>
      {sharing || roleMember ? (
        <SharingDialog<EditData['team']>
          name={team.name}
          schema={team.share_form}
          person={roleMember}
          api={initial.api_url}
          url={initialData.team_url}
          csrfToken={csrfToken}
          hostId={hostId}
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

export function SettingsPage({ initial, csrfToken }: PageProps) {
  const data = initial.data as EditData;
  const [preview, setPreview] = useState<Page>();
  const [open, setOpen] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    pageRequest<Page>(initial.api_url, data.dashboard.url, csrfToken, controller.signal)
      .then(setPreview)
      .catch(() => {
        /* The editor remains usable if its background cannot load. */
      });
    return () => controller.abort();
  }, [initial.api_url, data.dashboard.url, csrfToken]);
  return (
    <>
      {preview ? (
        <DashboardView initial={preview} csrfToken={csrfToken} />
      ) : (
        <div className="tasks-page work-page" />
      )}
      {open ? (
        <SettingsDialog
          initial={initial}
          csrfToken={csrfToken}
          onClose={() => {
            flushSync(() => setOpen(false));
            void navigate(data.return_url);
          }}
        />
      ) : null}
    </>
  );
}
