import { useRef, useState, useLayoutEffect } from 'react';
import { Avatar, type AvatarData } from './Avatar';
import { Icon } from './Icon';
import { dateLabel } from '../spaces/types';
export interface MemberRow {
  id: number | string;
  user_id: number;
  name: string;
  email: string;
  avatar: AvatarData;
  role: string;
  role_label: string;
  created_at: string | null;
  can_change: boolean;
}
export function Members({
  members,
  busy,
  selection,
}: {
  members: MemberRow[];
  busy: boolean;
  selection?: {
    selected: Set<number | string>;
    onChange: (next: Set<number | string>) => void;
  };
}) {
  const [localSelected, setLocalSelected] = useState<Set<number | string>>(() => new Set()),
    all = useRef<HTMLInputElement>(null);
  const currentSelection = selection?.selected ?? localSelected;
  const selected = new Set(
    members.filter((member) => currentSelection.has(member.id)).map((member) => member.id),
  );
  const selectedCount = selected.size;
  function setSelected(next: Set<number | string>) {
    if (busy) return;
    const allowed = new Set(
      members.filter((member) => next.has(member.id)).map((member) => member.id),
    );
    if (selection) selection.onChange(allowed);
    else setLocalSelected(allowed);
  }
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selectedCount > 0 && selectedCount < members.length;
  }, [selectedCount, members.length]);
  return (
    <div
      className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable workplace-team-sheet workplace-members-sheet app-data-table workplace-members-sheet--toolbar"
      tabIndex={0}
      role="region"
      aria-label="Członkowie — tabela"
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if ((event.ctrlKey || event.metaKey) && event.key === 'a') {
          event.preventDefault();
          setSelected(new Set(members.map((member) => member.id)));
        } else if (event.key === 'Escape') setSelected(new Set());
      }}
    >
      <section className="tasks-directory-group" role="table" aria-label="Członkowie zespołu">
        <div
          className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header app-table-header"
          role="row"
        >
          <span
            className="tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
            data-column="select"
            role="columnheader"
          >
            <input
              ref={all}
              type="checkbox"
              className="tasks-row-checkbox"
              aria-label="Zaznacz wszystkich członków"
              checked={members.length > 0 && selectedCount === members.length}
              disabled={busy || members.length === 0}
              onChange={(event) =>
                setSelected(
                  event.target.checked ? new Set(members.map((member) => member.id)) : new Set(),
                )
              }
            />
          </span>

          {[
            ['person', 'Nazwa', 'users'],
            ['email', 'E-mail', 'mail'],
            ['role', 'Rola', 'user-round'],
            ['joined', 'Dołączono', 'calendar-days'],
          ].map(([key, label, icon]) => (
            <span
              key={key}
              className="tasks-directory-sheet__cell tasks-project-sheet__cell"
              data-column={key}
              role="columnheader"
            >
              <Icon name={icon} />
              {label}
            </span>
          ))}
        </div>
        <div className="tasks-issue-list tasks-directory-list" role="rowgroup">
          {members.map((member) => (
            <div
              className={`tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row app-table-row ${selected.has(member.id) ? 'checked' : ''}`}
              role="row"
              key={member.id}
            >
              <input
                type="checkbox"
                className="tasks-row-checkbox tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="select"
                aria-label={`Zaznacz członka ${member.name}`}
                checked={selected.has(member.id)}
                disabled={busy}
                onChange={(event) => {
                  const next = new Set(selected);
                  if (event.target.checked) next.add(member.id);
                  else next.delete(member.id);
                  setSelected(next);
                }}
              />

              <div
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="person"
                role="cell"
              >
                <Avatar data={member.avatar} className="tasks-directory-avatar" />
                <span className="workplace-team__name" title={member.name}>
                  {member.name}
                </span>
              </div>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="email"
                role="cell"
                title={member.email}
              >
                <span className="workplace-team__name">{member.email}</span>
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="role"
                role="cell"
              >
                {member.role_label}
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="joined"
                role="cell"
              >
                {dateLabel(member.created_at) || '—'}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
