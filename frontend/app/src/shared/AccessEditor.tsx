import { useEffect, useRef, useState } from 'react';
import { Members, type MemberRow } from './Members';
import SharingDialog, { type SharingChange } from './SharingDialog';
import { Dropdown } from './Dropdown';
import { Icon } from './Icon';
import { PageError, pageRequest } from './page';
import { errorMessage } from './api';
import type { Team } from '../tasks/types';

export interface AccessTeam extends Team {
  name: string;
  visibility: string;
  revision: string | number;
  can_change_visibility: boolean;
  can_configure?: boolean;
  private_owner?: MemberRow;
}
type Draft = { visibility: string; members: MemberRow[] };
function draftFrom(team: AccessTeam, publicVisibility: string): Draft {
  return {
    visibility: team.visibility === publicVisibility ? publicVisibility : 'private',
    members:
      team.visibility === publicVisibility && team.private_owner
        ? [team.private_owner]
        : team.members.filter(
            (member) => team.visibility !== publicVisibility || member.role === 'owner',
          ),
  };
}
function draftKey(draft: Draft, publicVisibility: string) {
  return JSON.stringify([
    draft.visibility,
    draft.visibility === publicVisibility
      ? []
      : draft.members
          .filter((member) => member.role !== 'owner')
          .map((member) => [member.user_id, member.role])
          .sort((left, right) => Number(left[0]) - Number(right[0])),
  ]);
}

export default function AccessEditor<T extends AccessTeam>({
  team,
  publicVisibility = 'workspace',
  hostId,
  initialSharing = false,
  api,
  url,
  csrfToken,
  settingsDirty,
  blocked,
  onSaved,
  onStateChange,
}: {
  team: T;
  publicVisibility?: 'workspace' | 'public';
  hostId?: string;
  initialSharing?: boolean;
  api: string;
  url: string;
  csrfToken: string;
  settingsDirty: boolean;
  blocked: boolean;
  onSaved: (team: T) => void;
  onStateChange: (dirty: boolean, pending: boolean) => void;
}) {
  const [baseline, setBaseline] = useState(team);
  const [draft, setDraft] = useState(() => draftFrom(team, publicVisibility));
  const [selected, setSelected] = useState<Set<number | string>>(new Set());
  const [sharing, setSharing] = useState(initialSharing);
  const [roleMembers, setRoleMembers] = useState<MemberRow[]>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [conflict, setConflict] = useState(false);
  const [life] = useState(() => new AbortController());
  const sending = useRef(false);
  const dirty =
    draftKey(draft, publicVisibility) !==
    draftKey(draftFrom(baseline, publicVisibility), publicVisibility);
  const publicAccess = draft.visibility === publicVisibility;
  const visibilityChanged = publicAccess !== (baseline.visibility === publicVisibility);
  const busy = pending || blocked;
  const canManage = baseline.is_owner || baseline.can_manage;
  const selectedMembers = publicAccess
    ? []
    : draft.members.filter((member) => member.can_change && selected.has(member.id));
  const displayedMembers = publicAccess
    ? (baseline.visibility === publicVisibility ? baseline.members : draft.members).map((member) =>
        member.role === 'owner'
          ? member
          : { ...member, role: 'observer', role_label: 'Dostęp z Workspace', can_change: false },
      )
    : draft.members;

  useEffect(() => () => life.abort(), [life]);
  useEffect(() => onStateChange(dirty, pending), [dirty, pending, onStateChange]);
  useEffect(() => {
    // A settings-only save may advance the revision without changing the access draft.
    if (team === baseline) return;
    if (!dirty) {
      setBaseline(team);
      setDraft(draftFrom(team, publicVisibility));
    } else if (
      draftKey(draftFrom(team, publicVisibility), publicVisibility) ===
      draftKey(draftFrom(baseline, publicVisibility), publicVisibility)
    ) {
      setBaseline(team);
    }
  }, [team, baseline, dirty, publicVisibility]);

  function stage(next: Draft) {
    setDraft(next);
    setError('');
  }
  function stageSharing(change: SharingChange) {
    if (busy || publicAccess || !canManage) return;
    const roleField = baseline.share_form.fields.find((field) => field.name === 'role');
    const roleLabel =
      roleField?.choices?.find((choice) => choice.value === change.role)?.label || change.role;
    if ('people' in change) {
      const ids = new Set(
        change.people.filter((member) => member.can_change).map((member) => member.id),
      );
      stage({
        ...draft,
        members: draft.members.map((member) =>
          ids.has(member.id) && member.can_change
            ? { ...member, role: change.role, role_label: roleLabel }
            : member,
        ),
      });
    } else {
      const person = change.person;
      const userId = Number(person.id);
      if (!Number.isSafeInteger(userId) || userId <= 0) throw new Error('Wybierz osobę z listy.');
      if (draft.members.some((member) => member.user_id === userId))
        throw new Error('Ta osoba jest już na liście dostępu.');
      stage({
        ...draft,
        members: [
          ...draft.members,
          {
            id: `draft:${userId}`,
            user_id: userId,
            name: person.name,
            email: person.email,
            avatar: person.avatar,
            role: change.role,
            role_label: roleLabel,
            created_at:
              baseline.visibility === publicVisibility
                ? null
                : baseline.members.find((member) => member.user_id === userId)?.created_at || null,
            can_change: true,
          },
        ],
      });
    }
    setSharing(false);
    setRoleMembers(undefined);
    setSelected(new Set());
  }
  function removeSelected() {
    if (busy || !selectedMembers.length) return;
    const ids = new Set(selectedMembers.map((member) => member.id));
    stage({ ...draft, members: draft.members.filter((member) => !ids.has(member.id)) });
    setSelected(new Set());
  }
  function applySaved(result: T) {
    setBaseline(result);
    setDraft(draftFrom(result, publicVisibility));
    setSelected(new Set());
    setConflict(false);
    onSaved(result);
  }
  async function save() {
    if (sending.current || busy || !dirty || (settingsDirty && visibilityChanged)) return;
    sending.current = true;
    setPending(true);
    setError('');
    try {
      const body = new FormData();
      body.set('action', 'save');
      body.set('revision', String(baseline.revision));
      body.set('visibility', draft.visibility);
      body.set(
        'members',
        JSON.stringify(
          publicAccess
            ? []
            : draft.members
                .filter((member) => member.role !== 'owner')
                .map((member) => ({ user_id: member.user_id, role: member.role })),
        ),
      );
      const result = await pageRequest<T>(api, url, csrfToken, life.signal, body);
      if (!life.signal.aborted) {
        applySaved(result);
      }
    } catch (exception) {
      if (!life.signal.aborted) {
        setError(errorMessage(exception));
        setConflict(exception instanceof PageError && exception.status === 409);
      }
    } finally {
      sending.current = false;
      if (!life.signal.aborted) setPending(false);
    }
  }
  async function cancel() {
    if (sending.current || busy) return;
    if (!conflict) {
      setDraft(draftFrom(baseline, publicVisibility));
      setSelected(new Set());
      setError('');
      return;
    }
    sending.current = true;
    setPending(true);
    try {
      const result = await pageRequest<T>(api, url, csrfToken, life.signal);
      if (!life.signal.aborted) {
        applySaved(result);
        setError('');
      }
    } catch (exception) {
      if (!life.signal.aborted) setError(errorMessage(exception));
    } finally {
      sending.current = false;
      if (!life.signal.aborted) setPending(false);
    }
  }

  return (
    <>
      <div className="tasks-modal__body space-settings-table-body access-editor">
        <div className="tasks-filterbar tasks-filterbar--directory workplace-edit-modal__team-toolbar member-access-toolbar">
          <Dropdown
            label={`Widoczność: ${publicAccess ? 'Publiczna' : 'Prywatna'}`}
            searchable={false}
            disabled={busy || settingsDirty || !baseline.can_change_visibility}
            trigger={
              <>
                <Icon name={publicAccess ? 'users' : 'lock'} />
                <span>Widoczność: {publicAccess ? 'Publiczna' : 'Prywatna'}</span>
                <Icon name="chevron-down" />
              </>
            }
          >
            {(close) => (
              <div className="documents-menu-actions">
                {(
                  [
                    { value: publicVisibility, label: 'Publiczna — cały Workspace', icon: 'users' },
                    { value: 'private', label: 'Prywatna — wybrane osoby', icon: 'lock' },
                  ] as const
                ).map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    role="menuitemradio"
                    aria-checked={draft.visibility === option.value}
                    className="tasks-project-menu-button"
                    onClick={() => {
                      close();
                      stage({ ...draft, visibility: option.value });
                      setSelected(new Set());
                    }}
                  >
                    <Icon name={option.icon} />
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            )}
          </Dropdown>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={busy || !selectedMembers.length}
            onClick={() => setRoleMembers(selectedMembers)}
            aria-haspopup="dialog"
          >
            <Icon name="pencil" />
            Zmień rolę
          </button>
          <button
            type="button"
            className="tasks-filter-button"
            disabled={busy || !selectedMembers.length}
            onClick={removeSelected}
          >
            <Icon name="log-out" />
            Odbierz dostęp
          </button>
          {canManage ? (
            <button
              type="button"
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
              disabled={busy || publicAccess}
              onClick={() => setSharing(true)}
              aria-haspopup="dialog"
            >
              <Icon name="plus" />
              Udostępnij
            </button>
          ) : null}
          <div className="member-access-save-actions">
            <button
              type="button"
              className="tasks-tag-topbar-button tasks-tag-topbar-button--row-highlight"
              disabled={busy || !dirty || conflict || (settingsDirty && visibilityChanged)}
              onClick={() => void save()}
            >
              <Icon name="check" />
              {pending ? 'Zapisywanie…' : 'Zapisz'}
            </button>
            <button
              type="button"
              className="tasks-filter-button"
              disabled={busy || (!dirty && !selected.size && !error)}
              onClick={() => void cancel()}
            >
              Anuluj
            </button>
          </div>
        </div>
        {error ? (
          <p className="tasks-modal__errors" role="alert">
            {error}
            {conflict
              ? ' Wybierz „Anuluj”, aby odrzucić szkic i wczytać aktualny dostęp.'
              : ' Spróbuj ponownie przyciskiem „Zapisz”.'}
          </p>
        ) : null}
        {settingsDirty && baseline.can_change_visibility ? (
          <p className="workplace-team__hint">
            Zapisz zmiany w „Ustawieniach”, aby zmienić widoczność tutaj.
          </p>
        ) : null}
        <Members
          members={displayedMembers}
          isOwner={baseline.is_owner}
          busy={busy}
          rowActions={false}
          selection={{ selected, onChange: setSelected }}
        />
      </div>
      {sharing || roleMembers ? (
        <SharingDialog
          hostId={hostId}
          name={baseline.name}
          schema={baseline.share_form}
          people={roleMembers}
          api={api}
          url={url}
          candidatesUrl={url + 'candidates/?draft=1'}
          csrfToken={csrfToken}
          onStage={stageSharing}
          onClose={() => {
            setSharing(false);
            setRoleMembers(undefined);
          }}
        />
      ) : null}
    </>
  );
}
