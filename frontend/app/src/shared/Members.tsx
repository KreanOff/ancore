import { useRef, useState, useLayoutEffect } from 'react';
import { Avatar, type AvatarData } from './Avatar';
import { Dropdown } from './Dropdown';
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
  isOwner,
  busy,
  onRole,
  onRemove,
}: {
  members: MemberRow[];
  isOwner: boolean;
  busy: boolean;
  onRole: (member: MemberRow) => void;
  onRemove: (member: MemberRow) => void;
}) {
  const [selected, setSelected] = useState<Set<number | string>>(new Set()),
    all = useRef<HTMLInputElement>(null);
  useLayoutEffect(() => {
    if (all.current)
      all.current.indeterminate = selected.size > 0 && selected.size < members.length;
  }, [selected, members.length]);
  return (
    <div
      className="tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable workplace-team-sheet workplace-members-sheet"
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
          className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header"
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
              checked={members.length > 0 && selected.size === members.length}
              onChange={(event) =>
                setSelected(
                  event.target.checked ? new Set(members.map((member) => member.id)) : new Set(),
                )
              }
            />
          </span>
          <span
            className="tasks-directory-sheet__cell tasks-project-sheet__cell"
            data-column="action"
            role="columnheader"
            aria-label="Działania"
          />
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
              className={`tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row ${selected.has(member.id) ? 'checked' : ''}`}
              role="row"
              key={member.id}
            >
              <input
                type="checkbox"
                className="tasks-row-checkbox tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="select"
                aria-label={`Zaznacz członka ${member.name}`}
                checked={selected.has(member.id)}
                onChange={(event) =>
                  setSelected((current) => {
                    const next = new Set(current);
                    if (event.target.checked) next.add(member.id);
                    else next.delete(member.id);
                    return next;
                  })
                }
              />
              <div
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="action"
                role="cell"
              >
                {member.can_change ? (
                  <Dropdown
                    label={`Działania: ${member.name}`}
                    menuClass="documents-item-menu"
                    trigger={<Icon name="menu" />}
                  >
                    {(close) => (
                      <div className="documents-menu-actions">
                        {isOwner ? (
                          <button
                            type="button"
                            role="menuitem"
                            className="tasks-project-menu-button"
                            disabled={busy}
                            onClick={() => {
                              close();
                              onRole(member);
                            }}
                          >
                            <Icon name="pencil" />
                            <span>Zmień rolę</span>
                          </button>
                        ) : null}
                        <button
                          type="button"
                          role="menuitem"
                          className="tasks-project-menu-button"
                          disabled={busy}
                          onClick={() => {
                            close();
                            onRemove(member);
                          }}
                        >
                          <Icon name="log-out" />
                          <span>Odbierz dostęp</span>
                        </button>
                      </div>
                    )}
                  </Dropdown>
                ) : null}
              </div>
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
                {dateLabel(member.created_at)}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
