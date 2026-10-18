import { useLayoutEffect, useRef, useState } from 'react';
import { Avatar } from '../shared/Avatar';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { EmptyState } from '../shared/EmptyState';
import type { Person } from './types';
export default function TeamTable({
  rows,
  invitations = false,
  busy,
  onRole,
  onAction,
}: {
  rows: Person[];
  invitations?: boolean;
  busy: boolean;
  onRole: (person: Person) => void;
  onAction: (person: Person) => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(new Set()),
    all = useRef<HTMLInputElement>(null);
  const ids = rows.map((p) => p.id),
    count = ids.filter((id) => selected.has(id)).length;
  useLayoutEffect(() => {
    if (all.current) all.current.indeterminate = count > 0 && count < ids.length;
  }, [count, ids.length]);
  function toggle(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  if (!rows.length)
    return invitations ? (
      <EmptyState
        illustration="people"
        title="Brak oczekujących zaproszeń."
        description="Nowe osoby możesz dodać przyciskiem „Zaproś osobę”."
      />
    ) : (
      <EmptyState illustration="people" title="Brak członków." />
    );
  return (
    <div
      className={
        'tasks-table-wrap tasks-board tasks-directory-board tasks-directory-sheet tasks-project-sheet tasks-project-sheet--selectable workplace-team-sheet ' +
        (invitations ? 'workplace-invitations-sheet' : 'workplace-members-sheet')
      }
      tabIndex={0}
      role="region"
      aria-label={invitations ? 'Wysłane zaproszenia — tabela' : 'Członkowie — tabela'}
    >
      <section
        className="tasks-directory-group"
        role="table"
        aria-label={invitations ? 'Oczekujące zaproszenia' : 'Członkowie zespołu'}
      >
        <div
          className="tasks-directory-header tasks-directory-sheet__header tasks-project-sheet__header"
          role="row"
        >
          <span
            className="tasks-directory-header-select tasks-directory-sheet__cell tasks-project-sheet__cell"
            data-column="select"
            role="columnheader"
            onClick={(e) => {
              if (e.target === e.currentTarget) all.current?.click();
            }}
          >
            <input
              ref={all}
              type="checkbox"
              className="tasks-row-checkbox"
              aria-label={
                invitations
                  ? 'Zaznacz wszystkie wysłane zaproszenia'
                  : 'Zaznacz wszystkich członków'
              }
              checked={count === rows.length}
              onChange={(e) => setSelected(e.target.checked ? new Set(ids) : new Set())}
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
            [
              invitations ? 'expires' : 'joined',
              invitations ? 'Ważne do' : 'Dołączono',
              invitations ? 'calendar-clock' : 'calendar-days',
            ],
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
          {rows.map((person) => (
            <div
              key={person.id}
              className={
                'tasks-issue-row tasks-directory-row tasks-directory-sheet__row tasks-project-sheet__row ' +
                (selected.has(person.id) ? 'checked' : '')
              }
              role="row"
            >
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="select"
                role="cell"
                onClick={(e) => {
                  if (e.target === e.currentTarget) toggle(person.id);
                }}
              >
                <input
                  type="checkbox"
                  className="tasks-row-checkbox"
                  aria-label={
                    invitations
                      ? 'Zaznacz zaproszenie dla ' + person.email
                      : 'Zaznacz członka ' + person.name
                  }
                  checked={selected.has(person.id)}
                  onChange={() => toggle(person.id)}
                />
              </span>
              <div
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="action"
                role="cell"
              >
                {person.change_url || person.cancel_url ? (
                  <Dropdown
                    searchable={false}
                    className="documents-item-actions"
                    triggerClassName="tasks-project-sheet__edit-button"
                    menuClass="tasks-section-menu documents-item-menu"
                    label={'Działania: ' + (invitations ? person.email : person.name)}
                    trigger={<Icon name="menu" />}
                  >
                    {(close) => (
                      <div className="documents-menu-actions">
                        {person.can_role ? (
                          <button
                            type="button"
                            role="menuitem"
                            className="tasks-project-menu-button"
                            disabled={busy}
                            onClick={() => {
                              close();
                              onRole(person);
                            }}
                          >
                            <Icon name="pencil" />
                            Zmień rolę
                          </button>
                        ) : null}
                        <button
                          type="button"
                          role="menuitem"
                          className="tasks-project-menu-button"
                          disabled={busy}
                          onClick={() => {
                            close();
                            onAction(person);
                          }}
                        >
                          <Icon name={invitations ? 'x' : 'log-out'} />
                          {invitations ? 'Anuluj zaproszenie' : 'Odbierz dostęp'}
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
                <Avatar data={person.avatar} className="tasks-directory-avatar" />
                <span className="workplace-team__name" title={person.name}>
                  {person.name}
                  {person.self ? ' (Ty)' : ''}
                </span>
              </div>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="email"
                role="cell"
                title={person.email}
              >
                <span className="workplace-team__name">{person.email}</span>
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column="role"
                role="cell"
              >
                {person.role_label}
              </span>
              <span
                className="tasks-directory-sheet__cell tasks-project-sheet__cell"
                data-column={invitations ? 'expires' : 'joined'}
                role="cell"
              >
                {person.date}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
