import { useCallback, useEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { EmbeddedForm, type FormDialogData, type FormSection } from '../forms/FormDialog';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { Members, type MemberRow } from '../shared/Members';
import SharingDialog from '../shared/SharingDialog';
import { pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import type { FilterTeam } from './types';

const main: FormSection = {
  id: 'filter-settings-main',
  label: 'Ustawienia',
  fields: ['name', 'description', 'query', 'visibility'],
};
const tabs = [
  { id: main.id, label: 'Ustawienia', icon: 'settings' },
  { id: 'filter-settings-access', label: 'Udostępnienia', icon: 'users' },
];
const sections = [main];

export default function SettingsDialog({
  data,
  api,
  csrfToken,
  onClose,
  onSaved,
  hostId,
}: {
  data: FormDialogData;
  api: string;
  csrfToken: string;
  onClose: () => void;
  onSaved: (url: string) => void;
  hostId?: string;
}) {
  const [current, setCurrent] = useState(data);
  const [open, setOpen] = useState(true);
  const [team, setTeam] = useState(data.filter_team?.data);
  const [tab, setTab] = useState(main.id);
  const [state, setState] = useState({ dirty: data.form.bound, pending: false });
  const [revisionChange, setRevisionChange] = useState<{ previous: number; current: number }>();
  const [notice, setNotice] = useState(''),
    [error, setError] = useState('');
  const [sharing, setSharing] = useState(false),
    [roleMember, setRoleMember] = useState<MemberRow>();
  const [acting, setActing] = useState(false);
  const action = useRef(false),
    savedUrl = useRef('');
  const retry = useRef<(() => void) | undefined>();
  const [life] = useState(() => new AbortController());
  const pending = state.pending || acting;
  useEffect(() => () => life.abort(), [life]);
  const report = useCallback((dirty: boolean, pending: boolean) => {
    setState({ dirty, pending });
    if (dirty || pending) setNotice('');
  }, []);
  const close = () => {
    flushSync(() => setOpen(false));
    if (savedUrl.current) onSaved(savedUrl.current);
    else onClose();
  };
  function shared(result: FilterTeam) {
    setTeam(result);
    if (result.previous_revision !== undefined)
      setRevisionChange({ previous: result.previous_revision, current: result.revision });
    savedUrl.current ||= current.return_url;
    setSharing(false);
    setRoleMember(undefined);
    setNotice('Dostęp został zapisany.');
  }
  async function refreshTeam() {
    if (!current.filter_team) return;
    setActing(true);
    setError('');
    retry.current = undefined;
    try {
      const result = await pageRequest<FilterTeam>(
        api,
        current.filter_team.url,
        csrfToken,
        life.signal,
      );
      if (!life.signal.aborted) setTeam(result);
    } catch (exception) {
      if (!life.signal.aborted) {
        setError(errorMessage(exception));
        retry.current = () => void refreshTeam();
      }
    } finally {
      if (!life.signal.aborted) setActing(false);
    }
  }
  async function remove(member: MemberRow) {
    if (!current.filter_team || pending || action.current) return;
    action.current = true;
    setActing(true);
    setError('');
    retry.current = undefined;
    const body = new FormData();
    body.set('action', 'remove');
    body.set('member_id', String(member.id));
    try {
      const result = await pageRequest<FilterTeam>(
        api,
        current.filter_team.url,
        csrfToken,
        life.signal,
        body,
      );
      if (!life.signal.aborted) shared(result);
    } catch (exception) {
      if (!life.signal.aborted) {
        setError(errorMessage(exception));
        retry.current = () => void remove(member);
      }
    } finally {
      action.current = false;
      if (!life.signal.aborted) setActing(false);
    }
  }
  if (!open) return null;
  return (
    <>
      <Modal
        title={current.title}
        className="work-modal filter-settings-modal"
        hostId={hostId}
        dirty={state.dirty}
        pending={pending}
        onClose={close}
      >
        <div
          className="notifications-tabs filter-settings-tabs"
          role="tablist"
          aria-label={current.title}
          onKeyDown={(event) => {
            const index = tabs.findIndex((item) => item.id === tab);
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
            setTab(tabs[next].id);
            event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="tab"]')[next]?.focus();
          }}
        >
          {tabs.map((item) => (
            <button
              key={item.id}
              id={`${item.id}-tab`}
              type="button"
              role="tab"
              aria-selected={tab === item.id}
              aria-controls={`${item.id}-panel`}
              tabIndex={tab === item.id ? 0 : -1}
              disabled={pending}
              onClick={() => setTab(item.id)}
            >
              <Icon name={item.icon} />
              {item.label}
            </button>
          ))}
        </div>
        {error ? (
          <div className="tasks-modal__errors filter-settings-message" role="alert">
            {error}
            <button
              type="button"
              className="tasks-filter-button"
              disabled={pending}
              onClick={() => retry.current?.()}
            >
              Spróbuj ponownie
            </button>
          </div>
        ) : null}
        {notice ? (
          <p className="filter-settings-message" role="status">
            {notice}
          </p>
        ) : null}
        <div className="filter-settings-content" hidden={tab !== main.id}>
          <EmbeddedForm
            key={current.action}
            data={current}
            api={api}
            csrfToken={csrfToken}
            sections={sections}
            activeSection={main.id}
            onInvalidSection={setTab}
            onStateChange={report}
            revisionChange={revisionChange}
            onSaved={async (url, result) => {
              savedUrl.current = url;
              if (result?.filter_modal) {
                setCurrent(result.filter_modal);
                setTeam(result.filter_modal.filter_team?.data);
                setTab('filter-settings-access');
                setNotice('Filtr został zapisany. Możesz go teraz udostępnić.');
              } else {
                setNotice('Zmiany zostały zapisane.');
                await refreshTeam();
              }
            }}
          />
        </div>
        <section
          id="filter-settings-access-panel"
          role="tabpanel"
          aria-labelledby="filter-settings-access-tab"
          className="filter-settings-content"
          hidden={tab !== 'filter-settings-access'}
        >
          <div className="tasks-modal__body">
            {team ? (
              <>
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
                      message: `Odebrać dostęp do filtra osobie ${member.name}?`,
                      confirmText: 'Odbierz dostęp',
                      cancelText: 'Anuluj',
                      onConfirm: () => void remove(member),
                    })
                  }
                />
              </>
            ) : (
              <p className="workplace-team__hint">
                Zapisz filtr w zakładce „Ustawienia”, aby udostępnić go osobom z Workspace i wybrać
                ich role.
              </p>
            )}
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
        </section>
      </Modal>
      {(sharing || roleMember) && team && current.filter_team ? (
        <SharingDialog<FilterTeam>
          name={team.name}
          schema={team.share_form}
          person={roleMember}
          api={api}
          url={current.filter_team.url}
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
